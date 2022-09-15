signal_numpy = pyrunfile("import_data.py","signal");
t_numpy = pyrunfile("import_data.py", "t");

signal = cell2mat(cell(signal_numpy.tolist()));
t = cell2mat(cell(t_numpy.tolist()));

N = length(t)
observation_time = t(end);
Ts = t(2)-t(1);

Y = fft(signal-mean(signal));
P2 = abs(Y/N);
P1 = P2(1:N/2+1);
P1(2:end-1)=2*P1(2:end-1);

f=Ts^-1*(0:(N/2))/N; % take half the frequency points (only the positive points)
f2 = Ts^-1*((-N/2+1):(N/2))/N
plot(f2, P2)