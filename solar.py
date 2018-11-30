import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
import os
import pandas as pd
import time

import cntk as C

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

import cntk.tests.test_utils
cntk.tests.test_utils.set_device_from_pytest_env() # (only needed for our build system)

# to make things reproduceable, seed random
np.random.seed(0)

isFast = True

# we need around 2000 epochs to see good accuracy. For testing 100 epochs will do.
EPOCHS = 100 if isFast else 2000


def generate_solar_data(input_url, time_steps, normalize=1, val_size=0.1, test_size=0.1):
    """
    generate sequences to feed to rnn based on data frame with solar panel data
    the csv has the format: time ,solar.current, solar.total
     (solar.current is the current output in Watt, solar.total is the total production
      for the day so far in Watt hours)
    """
    # try to find the data file local. If it doesn't exists download it.
    cache_path = os.path.join("data", "iot")
    cache_file = os.path.join(cache_path, "solar.csv")
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)
    if not os.path.exists(cache_file):
        urlretrieve(input_url, cache_file)
        print("downloaded data successfully from ", input_url)
    else:
        print("using cache for ", input_url)

    df = pd.read_csv(cache_file, index_col="time", parse_dates=['time'], dtype=np.float32)

    df["date"] = df.index.date

    # normalize data
    df['solar.current'] /= normalize
    df['solar.total'] /= normalize

    # group by day, find the max for a day and add a new column .max
    grouped = df.groupby(df.index.date).max()
    grouped.columns = ["solar.current.max", "solar.total.max", "date"]

    # merge continuous readings and daily max values into a single frame
    df_merged = pd.merge(df, grouped, right_index=True, on="date")
    df_merged = df_merged[["solar.current", "solar.total",
                           "solar.current.max", "solar.total.max"]]
    # we group by day so we can process a day at a time.
    grouped = df_merged.groupby(df_merged.index.date)
    per_day = []
    for _, group in grouped:
        per_day.append(group)

    # split the dataset into train, validatation and test sets on day boundaries
    val_size = int(len(per_day) * val_size)
    test_size = int(len(per_day) * test_size)
    next_val = 0
    next_test = 0

    result_x = {"train": [], "val": [], "test": []}
    result_y = {"train": [], "val": [], "test": []}

    # generate sequences a day at a time
    for i, day in enumerate(per_day):
        # if we have less than 8 datapoints for a day we skip over the
        # day assuming something is missing in the raw data
        total = day["solar.total"].values
        if len(total) < 8:
            continue
        if i >= next_val:
            current_set = "val"
            next_val = i + int(len(per_day) / val_size)
        elif i >= next_test:
            current_set = "test"
            next_test = i + int(len(per_day) / test_size)
        else:
            current_set = "train"
        max_total_for_day = np.array(day["solar.total.max"].values[0])
        for j in range(2, len(total)):
            result_x[current_set].append(total[0:j])
            result_y[current_set].append([max_total_for_day])
            if j >= time_steps:
                break
    # make result_y a numpy array
    for ds in ["train", "val", "test"]:
        result_y[ds] = np.array(result_y[ds])
    return result_x, result_y


def next_batch(x, y, ds, batch_size):
    """get the next batch for training"""

    def as_batch(data, start, count):
        return data[start:start + count]

    for i in range(0, len(x[ds]), batch_size):
        yield as_batch(x[ds], i, batch_size), as_batch(y[ds], i, batch_size)


def create_model(x, h_dims):
    """Create the model for time series prediction"""
    with C.layers.default_options(initial_state = 0.1):
        m = C.layers.Recurrence(C.layers.LSTM(h_dims))(x)
        m = C.sequence.last(m)
        m = C.layers.Dropout(0.2)(m)
        m = C.layers.Dense(1)(m)
        return m


# validate
def get_mse(trainer, x_label, x, y, batch_size, l_label, labeltxt):
    result = 0.0
    for x1, y1 in next_batch(x, y, labeltxt, batch_size):
        eval_error = trainer.test_minibatch({x_label: x1, l_label: y1})
        result += eval_error
    return result/len(x[labeltxt])


def main():
    # We keep upto 14 inputs from a day
    TIMESTEPS = 14

    # 20000 is the maximum total output in our dataset. We normalize all values with
    # this so our inputs are between 0.0 and 1.0 range.
    NORMALIZE = 20000

    # process batches of 10 days
    BATCH_SIZE = TIMESTEPS * 10

    # Specify the internal-state dimensions of the LSTM cell
    H_DIMS = 15

    X, Y = generate_solar_data("https://www.cntk.ai/jup/dat/solar.csv",  TIMESTEPS, normalize=NORMALIZE)

    # input sequences
    x = C.sequence.input_variable(1)

    model_file = "solar.model"

    if not os.path.exists(model_file):
        print("Training model {}...".format(model_file))

        # create the model
        z = create_model(x, H_DIMS)

        # expected output (label), also the dynamic axes of the model output
        # is specified as the model of the label input
        var_l = C.input_variable(1, dynamic_axes=z.dynamic_axes, name="y")

        # the learning rate
        learning_rate = 0.005
        lr_schedule = C.learning_parameter_schedule(learning_rate)

        # loss function
        loss = C.squared_error(z, var_l)

        # use squared error to determine error for now
        error = C.squared_error(z, var_l)

        # use adam optimizer
        momentum_schedule = C.momentum_schedule(0.9, minibatch_size=BATCH_SIZE)
        learner = C.fsadagrad(z.parameters,
                              lr=lr_schedule,
                              momentum=momentum_schedule)
        trainer = C.Trainer(z, (loss, error), [learner])

        # training
        loss_summary = []

        start = time.time()
        for epoch in range(0, EPOCHS):
            for x_batch, l_batch in next_batch(X, Y, "train", BATCH_SIZE):
                trainer.train_minibatch({x: x_batch, var_l: l_batch})

            if epoch % (EPOCHS / 10) == 0:
                training_loss = trainer.previous_minibatch_loss_average
                loss_summary.append(training_loss)
                print("epoch: {}, loss: {:.4f}".format(epoch, training_loss))

        print("Training took {:.1f} sec".format(time.time() - start))

        # Print the train, validation and test errors
        for labeltxt in ["train", "val", "test"]:
            print("mse for {}: {:.6f}".format(labeltxt, get_mse(trainer, x, X, Y, BATCH_SIZE, var_l, labeltxt)))

        z.save(model_file)
    else:
        print("Loading existent model {}...".format(model_file))
        z = C.load_model(model_file)

    out = C.softmax(z)

    # Print out all layers in the model
    print('Loading {} and printing all layers:'.format(model_file))
    node_outputs = C.logging.get_node_outputs(z)
    for n in node_outputs:
        print("  {}".format(n))

    # predict
    # f, a = plt.subplots(2, 1, figsize=(12, 8))
    for j, ds in enumerate(["val", "test"]):
        fig = plt.figure()
        a = fig.add_subplot(2, 1, 1)
        results = []
        for x_batch, _ in next_batch(X, Y, ds, BATCH_SIZE):
            pred = out.eval({x: x_batch})
            results.extend(pred[:, 0])
        # because we normalized the input data we need to multiply the prediction
        # with SCALER to get the real values.
        a.plot((Y[ds] * NORMALIZE).flatten(), label=ds + ' raw')
        a.plot(np.array(results) * NORMALIZE, label=ds + ' pred')
        a.legend()

        fig.savefig("{}_chart.jpg".format(ds))


if __name__ == "__main__":
    main()