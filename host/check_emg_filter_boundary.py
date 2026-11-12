import numpy as np
from scipy.signal import butter,sosfilt
import usb_emg as u
n=np.arange(2000);t=n/1000
worst=0
for phase in np.linspace(0,2*np.pi,17):
    x=1850+80*np.sin(2*np.pi*50*t+phase)+20*np.cos(2*np.pi*100*t-phase)
    y=u.clean_offline(x)
    worst=max(worst,float(np.max(abs(y))))
assert worst<1e-8,worst
legacy=u.clean(1850+80*np.cos(2*np.pi*50*t))
assert np.sqrt(np.mean(legacy[:200]**2))>50,'negative control no longer reproduces'
burst=np.zeros(2000);burst[600:1400]=30*np.sin(2*np.pi*83*t[600:1400])
y=u.clean_offline(1850+80*np.cos(2*np.pi*50*t)+burst)
reference=sosfilt(butter(2,20,'highpass',fs=1000,output='sos'),burst)
assert np.sqrt(np.mean((y-reference)**2))<1.5
assert np.sqrt(np.mean(y[200:500]**2))<1.5 # limited noncausal leakage, not onset acceptance
for bad in [np.zeros(2), np.full(2000,np.nan)]:
    try:u.clean_offline(bad)
    except ValueError:pass
    else:raise AssertionError('invalid input accepted')
print('PASS: 17 mains phases suppressed, old artefact reproduced, known burst preserved within tolerance, invalid input rejected')
