import numpy as np
from scipy import signal,stats,fft
from spectrum import arburg,arma2psd,pburg
import statsmodels.regression.linear_model as transform


def Power_burg_calculation_optimization(Epoch_compute,noverlap,N_FFT,f_max, n_per_seg,smoothing,freqs_left,filter_order):
    #burg = pburg(Epoch_compute,15,NFFT = nfft_test)
    data = Epoch_compute[:,:]
    xs, ys = [], []
    a = data.shape
    M = a[1]
    #print(M)
    L = n_per_seg
    #print(L)
    noverlap = noverlap
    LminusOverlap = L-noverlap
    #print(LminusOverlap)
    k = round((M-noverlap)/(L-noverlap))
    #print(k)
    xStart = np.array(range(0,k*LminusOverlap,LminusOverlap))
    #print(xStart)
    xEnd = []
    for i in xStart:
        xEnd.append(i+L-1)
    xEnd = np.array(xEnd)
    #print(xEnd)
    fres =f_max/N_FFT
    power = []
    Block_spectrum= []
    
    tab = np.array(range(k-1))
    trialspectrum = np.zeros([a[0],N_FFT])
    PSD_final = np.zeros([a[0],round(f_max/2)])
    Time_freq = np.zeros([a[0],len(tab),round(f_max/(2*fres))])
    time = np.linspace(0,round(M/f_max),k-1)
    for i in range(a[0]):
        Block_spectrum = []
        for numBlock in tab:
            aux_condition1data = Epoch_compute[i,xStart[numBlock]:xEnd[numBlock]]

            aux_condition1data = signal.detrend(aux_condition1data,type='constant')

            AR, sigma2 = transform.burg(aux_condition1data, filter_order)
            PSD = arma2psd(-AR, NFFT = N_FFT,sides='centerdc')
            # plt.plot(PSD)
            # plt.show()
            Block_spectrum.append(PSD)
            Time_freq[i,numBlock]=PSD[round(f_max/(2*fres)):round(f_max/fres)]
            block = np.mean(Block_spectrum,axis=0)
            trialspectrum[i] = np.array(block)

    if smoothing == True:
        for k in range(a[0]):
             for l in range(a[1]):
                 PSD_final[k,l,0] = (trialspectrum[k,l,0] + trialspectrum[k,l,1] +trialspectrum[k,l,2])/3
                 PSD_final[k,l,round(f_max/2)-1] = (trialspectrum[k,l,freqs_left.shape[0]-3] + trialspectrum[k,l,freqs_left.shape[0]-2] +trialspectrum[k,l,freqs_left.shape[0]-1])/3
                 for i in range(5,freqs_left.shape[0]-2,round(1/fres)):
                     PSD_final[k,l,round(i/5)] = (trialspectrum[k,l,i-2] +trialspectrum[k,l,i-1] +trialspectrum[k,l,i] + trialspectrum[k,l,i+1] +trialspectrum[k,l,i+2])/(5)
        return PSD_final

    return trialspectrum[:,round(f_max/(2*fres)):round(f_max/fres)],Time_freq,time


def Power_burg_calculation(Epoch_compute,noverlap,N_FFT,f_max, n_per_seg,smoothing,freqs_left,filter_order):
    #burg = pburg(Epoch_compute,15,NFFT = nfft_test)
    data = Epoch_compute[:,:,:]
    xs, ys = [], []
    a = data.shape
    M = a[2]
    #print(M)
    L = n_per_seg
    #print(L)
    noverlap = noverlap
    LminusOverlap = L-noverlap
    #print(LminusOverlap)
    k = round((M-noverlap)/(LminusOverlap))
    #print(k)
    xStart = np.array(range(0,k*LminusOverlap,LminusOverlap))
    #print(xStart)
    xEnd = []
    for i in xStart:
        xEnd.append(i+L-1)
    xEnd = np.array(xEnd)
    #print(xEnd)
    
    fres =f_max/N_FFT
    power = []
    Block_spectrum= []
    
    tab = np.array(range(k-1))
    trialspectrum = np.zeros([a[0],a[1],N_FFT])
    PSD_final = np.zeros([a[0],a[1],round(f_max/2)])
    Time_freq = np.zeros([a[0],a[1],len(tab),round(f_max/(2*fres))])
    time = np.linspace(0,round(M/f_max),k-1)
    for i in range(a[0]):
        for j in range(a[1]):
            Block_spectrum = []
            for numBlock in tab:
                aux_condition1data = Epoch_compute[i,j,xStart[numBlock]:xEnd[numBlock]]

                aux_condition1data = signal.detrend(aux_condition1data,type='constant')

                AR, sigma2 = transform.burg(aux_condition1data, filter_order)
                PSD = arma2psd(-AR, NFFT = N_FFT,sides='centerdc')
                # plt.plot(PSD)
                # plt.show()
                Block_spectrum.append(PSD)

                Time_freq[i,j,numBlock]=PSD[round(f_max/(2*fres)):round(f_max/fres)]
            block = np.mean(Block_spectrum,axis=0)
            trialspectrum[i,j] = np.array(block)

    if smoothing == True:
        for k in range(a[0]):
             for l in range(a[1]):
                 PSD_final[k,l,0] = (trialspectrum[k,l,0] + trialspectrum[k,l,1] +trialspectrum[k,l,2])/3
                 PSD_final[k,l,round(f_max/2)-1] = (trialspectrum[k,l,freqs_left.shape[0]-3] + trialspectrum[k,l,freqs_left.shape[0]-2] +trialspectrum[k,l,freqs_left.shape[0]-1])/3
                 for i in range(5,freqs_left.shape[0]-2,round(1/fres)):
                     PSD_final[k,l,round(i/5)] = (trialspectrum[k,l,i-2] +trialspectrum[k,l,i-1] +trialspectrum[k,l,i] + trialspectrum[k,l,i+1] +trialspectrum[k,l,i+2])/(5)
        return PSD_final

    return trialspectrum[:,:,round(f_max/(2*fres)):round(f_max/fres)],Time_freq,time

def Power_calculation_welch_method(Epoch_compute,f_min,f_max,t_min,t_max,nfft,noverlap,nper_seg,pick,proje,averag,windowing, smoothing):
    #filtered = mne.filter.filter_data(Epoch_compute, 140, 7, 35)

    fres =f_max/nfft
    #psd_left,freqs_left = mne.time_frequency.psd_welch(Epoch_compute, fmin=f_min, fmax=f_max, tmin=t_min, tmax=t_max, n_fft=nfft, n_overlap=noverlap, n_per_seg=nper_seg, picks=pick, proj=proje, n_jobs=1, reject_by_annotation=True, average=averag, window=windowing, verbose=None)
    freqs_left,psd_left = signal.welch(Epoch_compute, fs=f_max, window=windowing, nperseg=nper_seg, noverlap=noverlap, nfft=nfft, detrend='constant', return_onesided=True, scaling='density', axis=- 1, average=averag)
    b = psd_left.shape
    #print(freqs_left.shape[0])
    PSD_final = np.zeros([b[0],b[1],round(f_max/2)])
    if smoothing == True:
        for k in range(b[0]):
             for l in range(b[1]):
                 PSD_final[k,l,0] = (psd_left[k,l,0] + psd_left[k,l,1] +psd_left[k,l,2])/3
                 PSD_final[k,l,round(f_max/2)-1] = (psd_left[k,l,freqs_left.shape[0]-3] + psd_left[k,l,freqs_left.shape[0]-2] +psd_left[k,l,freqs_left.shape[0]-1])/3
                 for i in range(5,freqs_left.shape[0]-2,round(1/fres)):
                     PSD_final[k,l,round(i/5)] = (psd_left[k,l,i-2] +psd_left[k,l,i-1] +psd_left[k,l,i] + psd_left[k,l,i+1] +psd_left[k,l,i+2])/(5)
        return PSD_final,freqs_left

                #avgdata2(i, :, countcond2) = mean(trialspectrum(ind-evaluationsPerBin/2:ind+evaluationsPerBin/2-1,:));
    #print(PSD_final.shape)
    return psd_left,freqs_left
