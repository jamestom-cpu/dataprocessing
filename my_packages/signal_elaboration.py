import numpy as np
import matplotlib.pyplot as plt
import scipy as sc
import scipy.fft as sc_fft
import os, sys
import re
import h5py

class Signal:
    # group all the elaboration tools in one class. 
    # this class is built to handle the data processing of a single measurement. 
    def __init__(self, observation_time, number_of_samples, signal=None):
        self.T = observation_time
        self.N = number_of_samples

        ##
        self.Ts = self.T / self.N
        self.fs = 1 / self.Ts
        self.f_Nyquist = self.fs / 2
        self.t = np.linspace(0, self.T, self.N)

        # two sided
        self.f2 = np.linspace(-self.f_Nyquist, self.f_Nyquist, int(self.N))

        # single sided
        self.f1 = np.linspace(0, self.f_Nyquist, int(self.N / 2))
        if signal is not None:
            self.signal = signal
            # perform fft
            self.raw_spectrum_2, self.raw_spectrum_1 = self.fft(signal, sides=0)

    def fft(self, signal=None, clip=False, plot=False, normalize=True, sides=1):
        if signal is None:
            signal = self.signal
        transform = sc_fft.fft(signal)
        N = signal.shape[0]
        p2 = np.abs(transform)

        if normalize:
            p2 = p2 / 2
        # I want the total power of the transform to be equal to the orginal power of the signal
        # so I normalize by dividing by N

        if N % 2 == 0:
            # 2 sided transform
            p2a = p2[:int(N / 2)]
            p2[-int(N / 2):] = p2a
            p2[:int(N / 2)] = p2a[::-1]

            # 1 sided transform
            p1 = p2.copy()
            p1 = p1[int(N / 2):]
            # if a signal is real, then the components of the one sided transform are double the components of the two sided transform
            p1[1:-2] = 2 * p1[1:-2]
        else:
            # 2 sided transform
            p2a = p2[:int((N + 1) / 2)]
            p2[-int((N + 1) / 2):] = p2a
            p2[:int((N - 1) / 2)] = p2a[:-1][::-1]

            # 1 sided transform
            p1 = p2.copy()
            p1 = p1[int((N - 1) / 2):]
            # if a signal is real, then the components of the one sided transform are double the components of the two sided transform
            p1[1:] = 2 * p1[1:]

        if sides == 1:
            return p1
        if sides == 2:
            return p2
        if sides == 0:
            return p2, p1

    def apply_conv_FIR_filter(self, signal, filt):
        self.FIR_spectr = self.fft(filt, sides=2)

        #         self.FIR_coherent_gain = np.average(self.FIR_spectr)
        #         self.FIR_coherent_power_gain = np.sqrt(np.average(self.FIR_spectr**2))
        self.filt_signal = np.convolve(filt, signal, "same")

        #         self.filt_signal_amp = self.filt_signal/self.FIR_coherent_gain
        #         self.filt_signal_pwr = self.filt_signal/self.FIR_coherent_power_gain

        return self.filt_signal

    def apply_window(self, signal, window, coherence="amplitude"):
        self.coherent_gain = np.average(window)
        self.coherent_power_gain = np.sqrt(np.average(window ** 2))

        raw_windowed_signal = signal * window

        if coherence == "amplitude":
            windowed_signal = raw_windowed_signal / self.coherent_gain
        elif coherence == "power":
            windowed_signal = raw_windowed_signal / self.coherent_power_gain
        else:
            print("retuning raw window")
            windowed_signal = raw_windowed_signal

        return windowed_signal

    def inspect_filter(self, signal, FIR, window=None, window_coherence="amplitude", ax=None):
        if ax == None:
            fig, ax = plt.subplots(1, 2, figsize=(18, 6), dpi=120)

        ntaps = FIR.shape[0]
        f_FIR = np.linspace(0, self.f_Nyquist, int((ntaps + 1) // 2))
        FIR_fz = self.fft(FIR, sides=2, normalize=False)[-f_FIR.shape[0]:]

        filt = self.apply_conv_FIR_filter(self.signal, FIR)

        ax[0].plot(self.f1, self.fft(signal), label="raw signal")
        ax[0].plot(self.f1, self.fft(filt), label="filtered")
        ax[0].plot(f_FIR, FIR_fz, '-k', label="filter frequency response")

        ax[0].set_xscale("log")
        ax[0].set_xlim([10e6, 2.5e9])
        ax[0].grid(True, which="both")
        ax[0].set_xlabel("f[Hz]")
        ax[0].set_ylabel("Spectrum Magnitude [V]")
        ax[0].set_ylim([0, 1.5])

        ax[1].plot(self.f1, 20 * np.log10(self.fft(signal)), label="raw signal")
        ax[1].plot(self.f1, 20 * np.log10(self.fft(filt)), label="filtered")
        ax[1].plot(f_FIR, 20 * np.log10(FIR_fz), '-k', label="filter frequency response")

        ax[1].set_ylim([-40, 5])
        ax[1].set_ylabel("Spectrum Magnitude[dB]")
        ax[1].set_xscale("log")
        ax[1].set_xlim([10e6, 2.5e9])
        ax[1].grid(True, which="both")
        ax[1].set_xlabel("f[Hz]")

        if window is not None:
            windowed = self.fft(self.apply_window(filt, window, coherence=window_coherence))

            ax[0].plot(self.f1, windowed, label="windowed and filtered")
            ax[1].plot(self.f1, 20 * np.log10(windowed), label="windowed and filtered")

        ax[0].legend()
        ax[1].legend()
        

        
        
class Batch_Generator():
    # this class defines a generator that loads filenames in an array until the numbering
    # returns to 1. Therefore all the measurements of the same point should be grouped in one batch. 
    # The batch generator expects a generator as input, that returns one at a time the filenames. 
    # In particular such a generator is defined as os.scandir(<directory_path>)
    def __init__(self, coordinates):
        self.__len__ = len(coordinates)
        self.coordinate_gen = iter(coordinates)
        self.current_batch = []
        self.number_of_batches_done = 0
    
    def __len__(self):
        return self.__len__
    
    def __iter__(self):
        return self
    
    def __next__(self):
        current_coordinates = next(self.coordinate_gen)
        current_name = "x"+current_coordinates[0]+"y"+current_coordinates[1]
        batch = [current_name+str(ii+1)+".csv" for ii in range(50)]

        self.current_batch=batch
        self.number_of_batches_done += 1

        return self.current_batch

def read_csv(filename):
    for row in open(filename):
        yield list(map(lambda x: float(x),row.split(",")[-2:]))


class ElaborateBatches(Signal):
    def __init__(self, directory, coordinates, observation_time, record_length):
        self.directory = directory
        self.coordinates = coordinates
        self.batch_generator = Batch_Generator(coordinates)
        super().__init__(observation_time=observation_time,  number_of_samples=record_length)

    def analyze_batch(self, batch, signal_processing_function, batch_path=None, batch_number = 1):
        # initialize
        elaborated =[]

        # batch properties
        batch_size = len(batch)

        # get coordinates of each point
        _, x_coordinate, y_coordinate, _ = re.split("x|y|.csv", batch[0])
        y_coordinate = ".".join([y_coordinate.split(".")[0], y_coordinate.split(".")[1][:2]])

        for ii, m in enumerate(batch):
            signal = np.array(list(read_csv(os.path.join(self.directory, m))))[:,1]
            elaborated.append(signal_processing_function(signal))

            # display operation complete
            sys.stdout.write('\r')
            sys.stdout.write("BATCH %d [%-50s] %d%% %-5s" % (batch_number, (ii + 1) * "=", 2 * (ii + 1), batch_path))
            sys.stdout.flush()

        elaborated = np.array(elaborated)

        return elaborated, x_coordinate, y_coordinate

    def get_average_spectrum(self, batch, signal_postprocessing=lambda x: x, batch_path=None, batch_number=1):

        spectrum,xx, yy = self.analyze_batch(
            batch, lambda x: self.fft(signal_postprocessing(x), sides=1),
            batch_path=batch_path, batch_number=batch_number
        )

        average_spectrum = spectrum.mean(axis=0)
        return average_spectrum, xx, yy

    def run_average_spectrum(self, archive_name, signal_postprocessing=lambda x: x,
                             save_location="", number_of_batches = float("inf"),
                             batch_path="", restart_generator=True, default_overwrite=False):
        points = []
        spectra = []

        # I give the possibility to specify the name of a group.
        # In this way I can update an archive with a new group if I wish to do so.
        # The way to specify a group name is to pass a tuple as the archive name
        if type(archive_name) is tuple:
            filename = archive_name[0]
            groupname = archive_name[1]
        else:
            filename = archive_name
        archive_path = os.path.join(save_location, filename+".h5")

        if restart_generator:
            self.batch_generator = Batch_Generator(self.coordinates)

        # open the hdf5 file. The file can already exist or be new.
        # check if file exists
        if os.path.exists(archive_path):
            mode = "a"
        else:
            mode = "w"

        hf = h5py.File(archive_path, mode)

        if "groupname" in locals():
            try:
                group = hf.create_group(groupname)
            except Exception as e:
                if "(name already exists)" in str(e):
                    if default_overwrite:
                        del hf[groupname]
                        group= hf.create_group(groupname)
                    else:
                        raise NameError("name already used for a group")
                else:
                    raise e

        else:
            group = hf

        while self.batch_generator.number_of_batches_done < number_of_batches:
            try:
                sys.stdout.write("\n")
                batch = next(self.batch_generator)
                spectrum, xx, yy = self.get_average_spectrum(
                    batch, signal_postprocessing,
                    batch_path=batch_path,  batch_number=self.batch_generator.number_of_batches_done
                )
                pp = group.create_group("point_" + str(self.batch_generator.number_of_batches_done))
                pp.create_dataset("coordinates", data=np.array([float(xx), float(yy)]))
                pp.create_dataset("spectrum", data=spectrum)
            except(StopIteration):
                print("ITERATION STOPPED : ", self.batch_generator.number_of_batches_done)
                break


        hf.close()