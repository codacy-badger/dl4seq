# This file shows how to build a naive model for multiple-outputs. Following assumptions are made
# All outputs are modelled by a separate parallel NN(InputAttention in this case).
# All outputs are different and their losses are summed to be used as final loss for back-propagation.
# Each of the parallel NN receives same input.

import pandas as pd
import numpy as np
import os
from tensorflow import keras

from dl4seq import InputAttentionModel
from dl4seq.utils import make_model


class MultiSite(InputAttentionModel):
    """ This is only for two outputs currently. """

    def train_data(self, **kwargs):
        train_x, train_y, train_label = self.fetch_data(self.data, **kwargs)

        inputs = [train_x]
        for out in range(self.outs):
            s0_train = np.zeros((train_x.shape[0], self.nn_config['enc_config']['n_s']))
            h0_train = np.zeros((train_x.shape[0], self.nn_config['enc_config']['n_h']))

            inputs = inputs + [s0_train, h0_train]

        return inputs, [train_label[:, 0], train_label[:, 1]]

    def build_nn(self):

        setattr(self, 'method', 'input_attention')
        print('building input attention')

        predictions = []
        enc_input = keras.layers.Input(shape=(self.lookback, self.ins), name='enc_input1')  # Enter time series data
        inputs = [enc_input]

        for out in range(self.outs):
            lstm_out1, h0, s0 = self._encoder(enc_input, self.nn_config['enc_config'], lstm2_seq=False, suf=str(out))
            act_out = keras.layers.LeakyReLU(name='leaky_relu_' + str(out))(lstm_out1)
            predictions.append(keras.layers.Dense(1)(act_out))
            inputs = inputs + [s0, h0]

        print('predictions: ', predictions)

        self.k_model = self.compile(model_inputs=inputs, outputs=predictions)

        return


if __name__ == "__main__":
    input_features = ['input1', 'input2', 'input3', 'input4', 'input5', 'input6', 'input8',
                  'input11']
    # column in dataframe to bse used as output/target
    outputs = ['target7', 'target8']

    data_config, nn_config, total_intervals = make_model(batch_size=4,
                                                         lookback=15,
                                                         inputs=input_features,
                                                         outputs=outputs,
                                                         lr=0.0001,
                                                         epochs=20,
                                                         val_fraction=0.3,  # TODO why less than 0.3 give error here?
                                                         test_fraction=0.3
                                                         )

    fname = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data\\nasdaq100_padding.csv")
    df = pd.read_csv(fname)
    df.index = pd.to_datetime(df['Date_Time2'])

    model = MultiSite(data_config=data_config,
                      nn_config=nn_config,
                      data=df,
                      intervals=total_intervals
                      )


    def loss(x, _y):
        mse1 = keras.losses.MSE(x[0], _y[0])
        mse2 = keras.losses.MSE(x[1], _y[1])

        return mse1 + mse2


    model.loss = loss

    model.build_nn()

    history = model.train_nn(indices='random', tensorboard=True)

    y, obs = model.predict()
    # acts = model.activations(st=0, en=1400)
