from happyfeat.lib.Statistical_analysis import *
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from matplotlib import cm
from matplotlib import colors

from happyfeat.lib.utils import find_nearest

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline

import mne
from mne.viz import plot_topomap
# from mne_connectivity.viz import plot_connectivity_circle

import pandas as pd
from scipy.stats import sem


def topo_plot(Rsquare, title, montageStr, customMontage, electrodes, freqMin, freqMax, fres, fs, scaleColormap, useSign):

    fig, ax = plt.subplots()

    useRange = False
    if freqMax > 0:
        useRange = True

    if montageStr == "custom":
        df = pd.read_csv(customMontage)
        # TODO : catch errors (file not existing, badly formatted...)
        ch_names = df.name.to_list()
        pos = df[['x', 'y', 'z']].values
        dig_ch_pos = dict(zip(ch_names, pos))

        if set(['Nz', 'LPA', 'RPA']).issubset(ch_names):
            idx_Nz = ch_names.index('Nz')
            idx_LPA = ch_names.index('LPA')
            idx_RPA = ch_names.index('RPA')
            montage_inter = mne.channels.make_dig_montage(ch_pos=dig_ch_pos, nasion=pos[idx_Nz], lpa=pos[idx_LPA], rpa=pos[idx_RPA])
            ind = [i for (i, channel) in enumerate(montage_inter.ch_names) if channel in electrodes]
            montage = montage_inter.copy()
            # Only keep the desired channels
            montage.ch_names = [montage_inter.ch_names[x] for x in ind]
            kept_channel_info = [montage_inter.dig[x + 3] for x in ind]
            # Keep the first three rows as they are the fiducial points information
            montage.dig = montage_inter.dig[0:3] + kept_channel_info
        else:
            montage_inter = mne.channels.make_dig_montage(ch_pos=dig_ch_pos)
            ind = [i for (i, channel) in enumerate(montage_inter.ch_names) if channel in electrodes]
            montage = montage_inter.copy()
            # Only keep the desired channels
            montage.ch_names = [montage_inter.ch_names[x] for x in ind]
            montage.dig = [montage_inter.dig[x] for x in ind]

    else:
        montage_inter = mne.channels.make_standard_montage(montageStr)
        ind = [i for (i, channel) in enumerate(montage_inter.ch_names) if channel in electrodes]
        montage = montage_inter.copy()
        # Only keep the desired channels
        montage.ch_names = [montage_inter.ch_names[x] for x in ind]
        kept_channel_info = [montage_inter.dig[x + 3] for x in ind]
        # Keep the first three rows as they are the fiducial points information
        montage.dig = montage_inter.dig[0:3] + kept_channel_info

    n_channels = len(montage.ch_names)
    fake_info = mne.create_info(ch_names=montage.ch_names, sfreq=fs / 2,
                                ch_types='eeg')

    rng = np.random.RandomState(0)
    data = rng.normal(size=(n_channels, 1)) * 1e-6
    fake_evoked = mne.EvokedArray(data, fake_info)
    fake_evoked.set_montage(montage)

    sizer = np.zeros([n_channels])

    if not useRange:
        freq = str(freqMin)
        for i in range(n_channels):
            for j in range(len(electrodes)):
                if montage.ch_names[i] == electrodes[j]:
                    sizer[i] = Rsquare[:, round(freqMin/fres)][j]
    else:
        freq = str(freqMin) + ":" + str(freqMax)
        for i in range(n_channels):
            for j in range(len(electrodes)):
                if montage.ch_names[i] == electrodes[j]:
                    sizer[i] = Rsquare[:, round(freqMin/fres):round(freqMax/fres)][j].mean()

    if scaleColormap:
        vmin = np.nanmin(Rsquare)
        vmax = np.nanmax(Rsquare)

    if not useSign:
        if not scaleColormap:
            vmin = 0.0
            vmax = 1.0
        divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=(vmax+vmin)/2, vmax=vmax)
        im, cn = plot_topomap(sizer, fake_evoked.info, sensors=False, names=montage.ch_names,
                              res=500, contours=0, image_interp='cubic', show=False,
                              cmap='jet', cnorm=divnorm, axes=ax, outlines='head')
    else:
        if not scaleColormap:
            vmin = -1.0
            vmax = 1.0
        divnorm = colors.TwoSlopeNorm(vmin=vmin, vcenter=0., vmax=vmax)
        im, cn = plot_topomap(sizer, fake_evoked.info, sensors=False, names=montage.ch_names,
                              res=500, contours=0, image_interp='cubic', show=False,
                              cmap='bwr', cnorm=divnorm, axes=ax, outlines='head')

    for tt in plt.findobj(fig, plt.Text):
        if tt.get_text() in montage.ch_names:
            tt.set_fontsize(9)
            tt.set_fontweight('bold')

    cbar = plt.colorbar(
        ax=ax, orientation='vertical', mappable=im,
    )
    cbar.set_label('R2 values')

    ax.set_title(title + freq + ' Hz', fontsize='large')

    fig.canvas.draw()


def time_frequency_map(time_freq, time, freqs, channel, fmin, fmax, fres, each_point, baseline, channel_array,
                       std_baseline, vmin, vmax, tlength):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14}

    fig, ax = plt.subplots()
    tf = time_freq.mean(axis=0)
    tf = np.transpose(tf[channel, :, :])
    PSD_baseline = baseline[channel, :]
    PSD_STD = std_baseline[channel, :]
    A = []
    for i in range(tf.shape[1]):
        A.append(np.divide((tf[:, i] - PSD_baseline), PSD_baseline) * 100)
    tf = np.transpose(A)

    frequencies = []

    time_seres = []
    print(time)
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i
    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i

    tf = tf[index_fmin:index_fmax + 1, :]
    if np.amin(tf) < 0:
        plt.imshow(tf, cmap='jet', aspect='auto', origin='lower', vmin=vmin, vmax=vmax)
    else:
        plt.imshow(tf,cmap='jet',aspect='auto',origin ='lower',vmin = vmin,vmax = vmax)
    size_time = len(time) / each_point

    for i in range(len(time)):
        if round(size_time) == 0:
            time_seres.append(str(time[i]))
        else:
            if i % (round(size_time)) == 0:
                if tlength < 10:
                    time_seres.append(str((round(time[i], 1))))
                else:
                    time_seres.append(str((round(time[i]))))
            else:
                time_seres.append('')

    sizing = round(len(freqs[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freqs[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequencies.append(str(round(i)))
        else:
            frequencies.append('')
    cm.get_cmap('jet')
    # plt.jet()
    ax.tick_params(axis='both', which='both', length=0)
    cbar = plt.colorbar()
    cbar.set_label('ERD/ERS', rotation=270, labelpad=10)
    plt.yticks(range(len(freqs[index_fmin:index_fmax + 1])), frequencies, fontsize=7)

    plt.xticks(range(len(time)), time_seres, fontsize=7)
    plt.xlabel(' Time (s)', fontdict=font)
    plt.ylabel('Frequency (Hz)', fontdict=font)

    # plt.show()

# Plot the two class comparison of PSDs, plus the R2 value for each freq, on the same graph
def plot_comparison_plotly(Power_class1, Power_class2, Rsquare, freqs, channel,
                           channel_array, each_point, fmin, fmax, fres,
                           class1label, class2label, metricLabel, isLog, title):

    STD_class2 = sem(Power_class2[:, channel, :], axis=0)
    STD_class1 = sem(Power_class1[:, channel, :], axis=0)
    
    if isLog:
        class2 = 10.0 * np.log10(Power_class2[:, channel, :])
        class1 = 10.0 * np.log10(Power_class1[:, channel, :])
    else:
        class2 = Power_class2[:, channel, :]
        class1 = Power_class1[:, channel, :]

    Aver_class2 = class2.mean(axis=0)
    Aver_class1 = class1.mean(axis=0)

    # find actual indices of frequencies
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i
            break
    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i
            break

    Selected_class2 = (Aver_class2[index_fmin:index_fmax])
    Selected_class1 = (Aver_class1[index_fmin:index_fmax])
    Selected_class2_STD = (STD_class2[index_fmin:index_fmax])
    Selected_class1_STD = (STD_class1[index_fmin:index_fmax])

    # Define traces
    xfreqs = freqs[index_fmin:index_fmax]

     # Create plot and add traces one after the other, + the "variance" areas for class 1 & 2
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # "Variance" traces
    factor = 1  # make it more visible
    fig.add_trace(go.Scatter(y=Selected_class1 - factor*Selected_class1_STD,
                             x=xfreqs, mode='lines', line_color='rgba(0,0,0,0)',
                             hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(y=Selected_class1 + factor*Selected_class1_STD,
                             x=xfreqs, mode='lines', line_color='rgba(0,0,0,0)',
                             hoverinfo='skip', showlegend=False, fill='tonexty', fillcolor='rgba(0,0,255,0.3)'))
    fig.add_trace(go.Scatter(y=Selected_class2 - factor*Selected_class2_STD,
                             x=xfreqs, mode='lines', line_color='rgba(0,0,0,0)',
                             hoverinfo='skip', showlegend=False))
    fig.add_trace(go.Scatter(y=Selected_class2 + factor*Selected_class2_STD,
                             x=xfreqs, mode='lines', line_color='rgba(0,0,0,0)',
                             hoverinfo='skip', showlegend=False, fill='tonexty', fillcolor='rgba(255,0,0,0.3)'))

    fig.add_trace(go.Scatter(y=Selected_class1, x=xfreqs, name=class1label,
                             mode='lines', line_color='rgba(0,0,255,1)', line_width=5))
    fig.add_trace(go.Scatter(y=Selected_class2, x=xfreqs, name=class2label,
                        mode='lines', line_color='rgba(255,0,0,1)', line_width=5))
    fig.add_trace(go.Scatter(y=Rsquare[channel, index_fmin:index_fmax], x=xfreqs, name="R2",
                        mode='lines', line_color='rgba(0,0,0,1)', line_width=5, yaxis='y2'), secondary_y=True)

    fulltitle = str(title +', Sensor: ' + channel_array[channel])
    fig.update_layout(title_text=fulltitle,
                      plot_bgcolor='white',
                      )
    fig.update_xaxes(title_text="Frequency (Hz)",
                     ticks='outside',
                     showline=True,
                     linecolor='black',
                     gridcolor='lightgrey')
    fig.update_yaxes(title_text=str(metricLabel),
                     ticks='outside',
                     showline=True,
                     linecolor='black',
                     gridcolor='lightgrey',
                     secondary_y=False)
    fig.update_yaxes(title_text="R2 value",
                     showgrid=False,
                     ticks='outside',
                     showline=True,
                     linecolor='black',
                     range=[0, 1],
                     secondary_y=True)

    return fig

def plot_Rsquare_calcul_welch(Rsquare, channel_array, freq, smoothing, fres, each_point, fmin, fmax, colormapScale, title):
    fig, ax = plt.subplots()
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14}
    frequencies = []

    nearest_fmin, index_fmin = find_nearest(freq, fmin)
    nearest_fmax, index_fmax = find_nearest(freq, fmax)


    Rsquare_reshape = Rsquare[0:len(channel_array), index_fmin:index_fmax + 1]

    vmin = 0
    vmax = 1
    if colormapScale:
        vmax = np.nanmax(abs(Rsquare_reshape))
        if np.nanmin(Rsquare_reshape) < 0:
            vmin = -np.amax(abs(Rsquare_reshape))

    plt.imshow(Rsquare_reshape, cmap='jet', aspect='auto', vmin=vmin, vmax=vmax)

    cm.get_cmap('jet')
    # plt.jet()
    cbar = plt.colorbar()
    cbar.set_label('R^2', rotation=270,labelpad = 10,fontsize = 20)
    cbar.ax.tick_params(labelsize=20)
    plt.yticks(range(len(channel_array)), channel_array)
    freq_real = range(0, round(freq[len(freq) - 1]), 2)
    sizing = round(len(freq[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freq[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequencies.append(str(round(i)))
        else:
            frequencies.append('')

    if smoothing:
        plt.xlim(0, 80)
    else:
        # plt.xticks(range(0,len(freq)-1,round(2/fres)),freq_real)
        # plt.xlim(0,round(70/fres))
        ax.tick_params(axis='both', which='both', length=0)
        plt.xticks(range(len(freq[index_fmin:index_fmax + 1])), frequencies, fontsize=10)
        # plt.xlim(0,round(72/fres))

    plt.xlabel('Frequency (Hz)', fontdict=font)
    plt.ylabel('Sensors', fontdict=font)

    # Major ticks
    ax.set_xticks(np.arange(0, len(freq[index_fmin:index_fmax + 1]), 1))
    ax.set_yticks(np.arange(0, len(channel_array), 1))

    # Labels for major ticks
    ax.set_xticklabels(frequencies)
    ax.set_yticklabels(channel_array)

    # Minor ticks
    ax.set_yticks(np.arange(-.5, len(channel_array), 1), minor=True)
    ax.set_xticks(np.arange(-.5, len(freq[index_fmin:index_fmax + 1]), 1), minor=True)
    # Gridlines based on minor ticks
    ax.grid(which='minor', color='black', linestyle='-', linewidth=1)
    # (ax.grid(axis ='minor',color = 'black',linewidth=1)
    plt.title(title)
    # Hplt.yticks(range(len(channel_array)),channel_array)
    # plt.show()

# New version of the R² map using plotly
def plot_Rsquare_plotly(Rsquare, channel_array, freq, fres, each_point, fmin, fmax, colormapScale, useSign, title):
    # Get frequencies to display
    frequencies = []
    nearest_fmin, index_fmin = find_nearest(freq, fmin)
    nearest_fmax, index_fmax = find_nearest(freq, fmax)
    frequencies = freq[index_fmin:index_fmax+1]

    # Only consider the useful part of the map
    Rsquare_reshape = Rsquare[0:len(channel_array), index_fmin:index_fmax + 1]

    # scaling
    vmin = 0
    vmax = 1
    if colormapScale:
        vmax = np.nanmax(abs(Rsquare_reshape))
        if np.nanmin(Rsquare_reshape) < 0:
            vmin = -np.amax(abs(Rsquare_reshape))

    # If "consider sign of Class2-Class1" btn is checked :
    # Blue (negative) to white (zero) to red (positive) colormap
    if useSign:
        fig = go.Figure(data=go.Heatmap(z=Rsquare_reshape,
                                        y=channel_array,
                                        x=frequencies,
                                        colorscale='RdBu_r',
                                        zmin=vmin,
                                        zmid=0,
                                        zmax=vmax))
    # Else (normal case) : jet colormap, from zero to max value
    else:
        fig = go.Figure(data=go.Heatmap(z=Rsquare_reshape,
                                        y=channel_array,
                                        x=frequencies,
                                        colorscale='jet',
                                        zmin=vmin,
                                        zmax=vmax))

    fig.update_layout(title_text=title,
                      plot_bgcolor='black',
                      yaxis_nticks=len(channel_array),
                      autosize=True
                      )
    fig.update_xaxes(title_text="Frequency (Hz)", showgrid=False)
    fig.update_yaxes(title_text="Channel", showgrid=False)

    return fig

def Reorder_plusplus(Rsquare, signTab, electrodes_orig, powerLeft, powerRight, timefreqLeft, timefreqRight):
    if len(electrodes_orig) == 74:
        # NETBCI...
        # electrodes_target = ['fp1', 'af7', 'af3', 'f7', 'f5', 'f3', 'f1', 'ft9', 'ft7', 'fc5', 'fc3', 'fc1',
        #              't9', 't7', 'c5', 'c3', 'c1', 'tp9', 'tp7', 'cp5', 'cp3', 'cp1', 'p9', 'p7',
        #              'p5', 'p3', 'p1', 'po3', 'po7', 'o1', 'po9', 'o9', 'fpz', 'afz', 'fz', 'fcz',
        #              'cz', 'cpz', 'pz', 'poz', 'oz', 'iz', 'fp2', 'af4', 'af8', 'f2', 'f4', 'f6',
        #              'f8', 'fc2', 'fc4', 'fc6', 'ft8', 'ft10', 'c2', 'c4', 'c6', 't8', 't10', 'cp2',
        #              'cp4', 'cp6', 'tp8', 'tp10', 'p2', 'p4', 'p6', 'p8', 'p10', 'po4', 'o2', 'po8',
        #              'o10', 'po10']

        electrodes_target = ['FP1', 'FPz', 'FP2', 'AF1', 'AF3', 'AFz', 'AF4',
                             'AF8', 'F7',  'F5',  'F3',   'F1',   'Fz',  'F2',
                             'F4',  'F6',  'F8', 'FT9',  'FT7', 'FC5', 'FC3',
                             'FC1', 'FCz', 'FC2', 'FC4', 'FC6', 'FT8', 'FT10',
                             'T9',  'T7',   'C5',  'C3',  'C1', 'Cz', 'C2', 'C4',
                             'C6',  'T8',  'T10', 'TP9', 'TP7', 'CP5',  'CP3', 'CP1', 'CPz',
                             'CP2', 'CP4', 'CP6', 'TP8', 'TP10', 'P9',
                             'P7',   'P3',  'P1',  'Pz',  'P2',  'P4',
                             'P6',   'P8', 'P10',  'PO9', 'PO7', 'PO5',
                             'PO3', 'POz', 'PO4',  'PO8', 'PO10', 'O1',
                             'Oz',   'O2',  'O9',   'IZ', 'O10']

    elif len(electrodes_orig) >= 64:
        electrodes_target = ['Fp1','AF7','AF3','F7','F5','F3','F1','FT9','FT7','FC5','FC3','FC1','T7','C5','C3','C1','TP7','CP5','CP3','CP1','P7','P5','P3','P1','PO7','PO3','O1','Fpz','AFz','Fz','FCz','Cz','CPz','Pz','POz','Oz','Iz','Fp2','AF8','AF4','F8','F6','F4','F2','FT10','FT8','FC6','FC4','FC2','T8','C6','C4','C2','TP8','CP6','CP4','CP2','P8','P6','P4','P2','PO8','PO4','O2']
    else:
        electrodes_target = ['Fp1', 'F7', 'F3', 'FC5', 'FC1', 'T7', 'C3', 'CP5', 'CP1', 'P7', 'P3', 'PO9', 'O1', 'AFz',
                             'Fz', 'FCz', 'Cz', 'Pz', 'Oz', 'Fp2', 'F8', 'F4', 'FC6', 'FC2', 'T8', 'C4', 'CP6', 'CP2',
                             'P8', 'P4', 'PO10', 'O2']
    index_elec = []
    electrode_array_final = []
    if len(electrodes_orig) == 74:
        # NETBCI...
        index_elec = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                      17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
                      32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46,
                      47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
                      62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73]

    else:
        for k in range(len(electrodes_target)):
            for i in range(len(electrodes_orig)):
                if electrodes_orig[i].casefold() == electrodes_target[k].casefold():
                    index_elec.append(i)
                    electrode_array_final.append(electrodes_orig[i])
                    break

    print(index_elec)

    Rsquare_final = np.zeros([Rsquare.shape[0], Rsquare.shape[1]])
    print(powerLeft.shape)
    signTab_final = np.zeros([signTab.shape[0], signTab.shape[1]])
    powerLeft_final = np.zeros([powerLeft.shape[0], powerLeft.shape[1], powerLeft.shape[2]])
    powerRight_final = np.zeros([powerRight.shape[0], powerRight.shape[1], powerRight.shape[2]])
    timefreqLeftfinal = np.zeros(
        [timefreqLeft.shape[0], timefreqLeft.shape[1], timefreqLeft.shape[2], timefreqLeft.shape[3]])
    timefreqRightfinal = np.zeros(
        [timefreqRight.shape[0], timefreqRight.shape[1], timefreqRight.shape[2], timefreqLeft.shape[3]])

    electrode_test = []
    electrode_final = []
    for l in range(len(index_elec)):
        # print("index "+str(l)+" replaced by "+str(index_elec[l]))
        electrode_test.append(index_elec[l])
        electrode_final.append(electrodes_orig[index_elec[l]])
        powerLeft_final[:, l, :] = powerLeft[:, index_elec[l], :]
        powerRight_final[:, l, :] = powerRight[:, index_elec[l], :]
        timefreqLeftfinal[:, l, :, :] = timefreqLeft[:, index_elec[l], :, :]
        timefreqRightfinal[:, l, :, :] = timefreqRight[:, index_elec[l], :, :]
        Rsquare_final[l, :] = Rsquare[index_elec[l], :]
        signTab_final[l, :] = signTab[index_elec[l], :]

    return Rsquare_final, signTab_final, electrode_final, powerLeft_final, powerRight_final, timefreqLeftfinal, timefreqRightfinal

def Reorder_custom(Rsquare, customPath, electrodes_orig, powerLeft, powerRight):

    df = pd.read_csv(customPath)
    electrodes_target = df.name.to_list()

    index_elec = []
    for k in range(len(electrodes_target)):
        for i in range(len(electrodes_orig)):
            if electrodes_orig[i].casefold() == electrodes_target[k].casefold():
                index_elec.append(i)
                break

    print(index_elec)

    Rsquare_final = np.zeros([Rsquare.shape[0], Rsquare.shape[1]])
    print(powerLeft.shape)
    powerLeft_final = np.zeros([powerLeft.shape[0], powerLeft.shape[1], powerLeft.shape[2]])
    powerRight_final = np.zeros([powerRight.shape[0], powerRight.shape[1], powerRight.shape[2]])

    electrode_test = []
    electrode_final = []
    for l in range(len(index_elec)):
        # print("index "+str(l)+" replaced by "+str(index_elec[l]))
        electrode_test.append(index_elec[l])
        electrode_final.append(electrodes_orig[index_elec[l]])
        powerLeft_final[:, l, :] = powerLeft[:, index_elec[l], :]
        powerRight_final[:, l, :] = powerRight[:, index_elec[l], :]
        Rsquare_final[l, :] = Rsquare[index_elec[l], :]

    return Rsquare_final, electrode_final, powerLeft_final, powerRight_final

def Reorder_custom_plus(Rsquare, signTab, customPath, electrodes_orig, powerLeft, powerRight, timefreqLeft, timefreqRight):

    df = pd.read_csv(customPath, usecols=[0])
    electrodes_target = df[df.columns.tolist()[0]].tolist()

    index_elec = []
    for k in range(len(electrodes_target)):
        for i in range(len(electrodes_orig)):
            if electrodes_orig[i].casefold() == electrodes_target[k].casefold():
                index_elec.append(i)
                break

    print(index_elec)

    Rsquare_final = np.zeros([Rsquare.shape[0], Rsquare.shape[1]])
    print(powerLeft.shape)
    signTab_final = np.zeros([signTab.shape[0], signTab.shape[1]])
    powerLeft_final = np.zeros([powerLeft.shape[0], powerLeft.shape[1], powerLeft.shape[2]])
    powerRight_final = np.zeros([powerRight.shape[0], powerRight.shape[1], powerRight.shape[2]])
    timefreqLeftfinal = np.zeros(
        [timefreqLeft.shape[0], timefreqLeft.shape[1], timefreqLeft.shape[2], timefreqLeft.shape[3]])
    timefreqRightfinal = np.zeros(
        [timefreqRight.shape[0], timefreqRight.shape[1], timefreqRight.shape[2], timefreqLeft.shape[3]])

    electrode_test = []
    electrode_final = []
    for l in range(len(index_elec)):
        # print("index "+str(l)+" replaced by "+str(index_elec[l]))
        electrode_test.append(index_elec[l])
        electrode_final.append(electrodes_orig[index_elec[l]])
        powerLeft_final[:, l, :] = powerLeft[:, index_elec[l], :]
        powerRight_final[:, l, :] = powerRight[:, index_elec[l], :]
        timefreqLeftfinal[:, l, :, :] = timefreqLeft[:, index_elec[l], :, :]
        timefreqRightfinal[:, l, :, :] = timefreqRight[:, index_elec[l], :, :]
        Rsquare_final[l, :] = Rsquare[index_elec[l], :]
        signTab_final[l, :] = signTab[index_elec[l], :]

    return Rsquare_final, signTab_final, electrode_final, powerLeft_final, powerRight_final, timefreqLeftfinal, timefreqRightfinal



def Reorder_Rsquare(Rsquare, electrodes_orig, powerLeft, powerRight):
    if len(electrodes_orig) == 74:
        # NETBCI...
        # electrodes_target = ['fp1', 'af7', 'af3', 'f7', 'f5', 'f3', 'f1', 'ft9', 'ft7', 'fc5', 'fc3', 'fc1',
        #               't9', 't7', 'c5', 'c3', 'c1', 'tp9', 'tp7', 'cp5', 'cp3', 'cp1', 'p9', 'p7',
        #               'p5', 'p3', 'p1', 'po3', 'po7', 'o1', 'po9', 'o9', 'fpz', 'afz', 'fz', 'fcz',
        #               'cz', 'cpz', 'pz', 'poz', 'oz', 'iz', 'fp2', 'af4', 'af8', 'f2', 'f4', 'f6',
        #               'f8', 'fc2', 'fc4', 'fc6', 'ft8', 'ft10', 'c2', 'c4', 'c6', 't8', 't10', 'cp2',
        #               'cp4', 'cp6', 'tp8', 'tp10', 'p2', 'p4', 'p6', 'p8', 'p10', 'po4', 'o2', 'po8',
        #               'o10', 'po10']
        electrodes_target = ['FP1', 'FPz', 'FP2', 'AF1', 'AF3', 'AFz', 'AF4',
                             'AF8', 'F7', 'F5', 'F3', 'F1', 'Fz', 'F2',
                             'F4', 'F6', 'F8', 'FT9', 'FT7', 'FC5', 'FC3',
                             'FC1', 'FCz', 'FC2', 'FC4', 'FC6', 'FT8', 'FT10',
                             'T9', 'T7', 'C5', 'C3', 'C1', 'Cz', 'C2',  'C4',
                             'C6', 'T8', 'T10', 'TP9', 'TP7', 'CP5', 'CP3', 'CP1', 'CPz',
                             'CP2', 'CP4', 'CP6', 'TP8', 'TP10', 'P9',
                             'P7', 'P3', 'P1', 'Pz', 'P2', 'P4',
                             'P6', 'P8', 'P10', 'PO9', 'PO7', 'PO5',
                             'PO3', 'POz', 'PO4', 'PO8', 'PO10', 'O1',
                             'Oz', 'O2', 'O9', 'IZ', 'O10']

    elif len(electrodes_orig) >= 64:
        electrodes_target = ['Fp1','AF7','AF3','F7','F5','F3','F1','FT9','FT7','FC5','FC3','FC1','T7','C5','C3','C1','TP7','CP5','CP3','CP1','P7','P5','P3','P1','PO7','PO3','O1','Fpz','AFz','Fz','FCz','Cz','CPz','Pz','POz','Oz','Iz','Fp2','AF8','AF4','F8','F6','F4','F2','FT10','FT8','FC6','FC4','FC2','T8','C6','C4','C2','TP8','CP6','CP4','CP2','P8','P6','P4','P2','PO8','PO4','O2']
    elif len(electrodes_orig) == 32:
        electrodes_target = ['Fp1', 'F7', 'F3', 'FC5', 'FC1', 'T7', 'C3', 'CP5', 'CP1', 'P7', 'P3', 'PO9', 'O1', 'AFz',
                             'Fz', 'FCz', 'Cz', 'Pz', 'Oz', 'Fp2', 'F8', 'F4', 'FC6', 'FC2', 'T8', 'C4', 'CP6', 'CP2',
                             'P8', 'P4', 'PO10', 'O2']
    elif len(electrodes_orig) == 11:
        electrodes_target = ['FC4', 'C2', 'C4', 'C6', 'CP4', 'Nz', 'CP3', 'C1', 'C3', 'C5', 'FC3']

    index_elec = []

    if len(electrodes_orig) == 74:
        # NETBCI...
        index_elec = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
                      17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
                      32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46,
                      47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61,
                      62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73]

    else:
        for k in range(len(electrodes_target)):
            found = False
            for i in range(len(electrodes_orig)):
                if electrodes_orig[i].casefold() == electrodes_target[k].casefold():
                    index_elec.append(i)
                    found = True
                    break
            if not found:
                print("Electrode " + electrodes_target[k] + " not found in original list!")


    print(index_elec)

    Rsquare_final = np.zeros([Rsquare.shape[0], Rsquare.shape[1]])
    print(powerLeft.shape)
    powerLeft_final = np.zeros([powerLeft.shape[0], powerLeft.shape[1], powerLeft.shape[2]])
    powerRight_final = np.zeros([powerRight.shape[0], powerRight.shape[1], powerRight.shape[2]])

    electrode_test = []
    electrode_final = []
    for l in range(len(index_elec)):
        # print("index "+str(l)+" replaced by "+str(index_elec[l]))
        electrode_test.append(index_elec[l])
        electrode_final.append(electrodes_orig[index_elec[l]])
        powerLeft_final[:, l, :] = powerLeft[:, index_elec[l], :]
        powerRight_final[:, l, :] = powerRight[:, index_elec[l], :]
        Rsquare_final[l, :] = Rsquare[index_elec[l], :]

    return Rsquare_final, electrode_final, powerLeft_final, powerRight_final

def plot_Wsquare_calcul_welch(Rsquare, channel_array, freq, smoothing, fres, each_point, fmin, fmax):
    fig, ax = plt.subplots()
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }
    frequencies = []

    nearest_fmin, index_fmin = find_nearest(freq, fmin)
    nearest_fmax, index_fmax = find_nearest(freq, fmax)
    Rsquare_reshape = Rsquare[0:len(channel_array), index_fmin:index_fmax + 1]

    if np.amin(Rsquare_reshape) < 0:
        plt.imshow(Rsquare_reshape, cmap='jet', aspect='auto', vmin=-np.amax(abs(Rsquare_reshape)),
                   vmax=np.max(abs(Rsquare_reshape)))
    else:
        plt.imshow(Rsquare_reshape, cmap='jet', aspect='auto')
    cm.get_cmap('jet')
    # plt.jet()
    cbar = plt.colorbar()
    cbar.set_label('Wilcoxon Signed Values', rotation=270, labelpad=10)
    plt.yticks(range(len(channel_array)), channel_array)
    freq_real = range(0, round(freq[len(freq) - 1]), 2)
    sizing = round(len(freq[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freq[index_fmin:(index_fmax + 1)]:
        if (i % (round(sizing * 1 / fres)) == 0):
            frequencies.append(str(round(i)))
        else:
            frequencies.append('')

    if smoothing:
        plt.xlim(0, 80)
    else:
        # plt.xticks(range(0,len(freq)-1,round(2/fres)),freq_real)
        # plt.xlim(0,round(70/fres))
        ax.tick_params(axis='both', which='both', length=0)
        plt.xticks(range(len(freq[index_fmin:index_fmax + 1])), frequencies, fontsize=10)
        # plt.xlim(0,round(72/fres))
    plt.xlabel('Frequency (Hz)', fontdict=font)
    plt.ylabel('Sensors', fontdict=font)

    # Major ticks
    ax.set_xticks(np.arange(0, len(freq[index_fmin:index_fmax + 1]), 1))
    ax.set_yticks(np.arange(0, len(channel_array), 1))

    # Labels for major ticks
    ax.set_xticklabels(frequencies)
    ax.set_yticklabels(channel_array)

    # Minor ticks

    ax.set_yticks(np.arange(-.5, len(channel_array), 1), minor=True)
    ax.set_xticks(np.arange(-.5, len(freq[index_fmin:index_fmax + 1]), 1), minor=True)
    # Gridlines based on minor ticks
    ax.grid(which='minor', color='black', linestyle='-', linewidth=1)


def time_frequency_map_between_cond(time_freq, time, freqs, channel, fmin, fmax, fres, each_point, baseline,
                                    channel_array):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }

    fig, ax = plt.subplots()
    rsquare_signed = Compute_Signed_Rsquare(time_freq[:, channel, :, :], baseline[:, channel, :, :])
    rsquare_signed = np.transpose(rsquare_signed)
    frequencies = []

    time_seres = []
    print(time)
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i
    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i

    rsquare_signed = rsquare_signed[index_fmin:index_fmax + 1, :]
    if np.amin(rsquare_signed) < 0:
        plt.imshow(rsquare_signed, cmap='jet', aspect='auto', origin='lower', vmin=-np.amax(rsquare_signed),
                   vmax=np.amax(rsquare_signed))
    else:
        plt.imshow(rsquare_signed, cmap='jet', aspect='auto', origin='lower')
    size_time = len(time) / each_point
    if round(size_time) == 0:
        size_time = 1

    for i in range(len(time)):
        if i % (round(size_time)) == 0:
            time_seres.append(str((round(time[i], 1))))
        else:
            time_seres.append('')

    sizing = round(len(freqs[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freqs[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequencies.append(str(round(i)))
        else:
            frequencies.append('')
    cm.get_cmap('jet')
    # plt.jet()
    ax.tick_params(axis='both', which='both', length=0)
    cbar = plt.colorbar()
    cbar.set_label('Signed R^2', rotation=270, labelpad=10)
    plt.yticks(range(len(freqs[index_fmin:index_fmax + 1])), frequencies, fontsize=7)

    plt.xticks(range(len(time)), time_seres, fontsize=7)
    plt.xlabel(' Time (s)', fontdict=font)
    plt.ylabel('Frequency (Hz)', fontdict=font)
    plt.title('Sensor ' + channel_array[channel], fontdict=font)


def plot_connect_spectrum(connect1, connect2, chan1idx, chan2idx, electrodeList, each_point, fres, class1label, class2label):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }

    fig, ax = plt.subplots()
    frequencies = []
    avg_class1 = connect1[:, :, chan1idx, chan2idx].mean(axis=0)
    avg_class2 = connect2[:, :, chan1idx, chan2idx].mean(axis=0)

    # Only plot half of the spectrum, since it's mirrored
    sizeSpectrum = int(np.floor((len(avg_class1)+1) / 2))

    plt.plot(avg_class1[0:sizeSpectrum], label=class1label, color='blue')
    plt.plot(avg_class2[0:sizeSpectrum], label=class2label, color='red')
    ax.tick_params(axis='both', which='both', length=0)

    plt.title('Connectivity btw. ' + electrodeList[chan1idx] + ' and ' + electrodeList[chan2idx], fontsize='large')
    # plt.xticks(range(len(freqs[index_fmin:(index_fmax + 1)])), frequencies, fontsize=12)
    plt.xlabel(' Frequency (Hz)', fontdict=font)
    plt.ylabel('MSC', fontdict=font)
    plt.margins(x=0)
    # ax.set_xticks(np.arange(fmin, fmax, sizing))
    ax.grid(axis='x')
    # plt.axis('square')

    plt.legend()
    # plt.show()


def plot_connect_matrices(connect1, connect2, fmin, fmax, channel_array, class1label, class2label):
    fig, axes = plt.subplots(ncols=2)
    ax1, ax2 = axes

    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14}

    connect1disp = connect1[:, fmin:fmax, :, :].mean(axis=0).mean(axis=0)
    connect2disp = connect2[:, fmin:fmax, :, :].mean(axis=0).mean(axis=0)

    top = cm.get_cmap('YlOrRd_r', 128)  # r means reversed version
    bottom = cm.get_cmap('YlGnBu_r', 128)
    newcolors2 = np.vstack((bottom(np.linspace(0, 1, 128)), top(np.linspace(1, 0, 128))))
    cm.get_cmap('jet')

    # Display matrices...
    im1 = ax1.imshow(connect1disp, cmap='jet', aspect='auto', vmin=0, vmax=1)
    im2 = ax2.imshow(connect2disp, cmap='jet', aspect='auto', vmin=0, vmax=1)

    # Set labels for both graphs...
    plt.setp(axes,
             xticks=range(0, len(channel_array)),
             xticklabels=channel_array,
             yticks=range(0, len(channel_array)),
             yticklabels=channel_array)

    # Put labels on top...
    ax1.xaxis.tick_top()
    ax2.xaxis.tick_top()

    # Set left/right titles...
    ax1.title.set_text(class1label)
    ax2.title.set_text(class2label)

    # Enable color bars...
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar2 = plt.colorbar(im2, ax=ax2)

    fig.suptitle("MSC for frequency band " + str(fmin) + " to " + str(fmax) + "Hz")

def plot_strongestConnectome(connect1, connect2, percentStrong, fmin, fmax, electrodeList, class1label, class2label):
    f, axes = plt.subplots(num=2, facecolor='black')
    connect1disp = connect1[:, fmin:fmax, :, :].mean(axis=0).mean(axis=0)
    sortedVec = np.sort(connect1disp, axis=None)
    idxPercent = int(np.floor(len(sortedVec) * (100 - percentStrong) / 100))
    connect1disp = (connect1disp >= sortedVec[idxPercent]) * connect1disp

    connect2disp = connect2[:, fmin:fmax, :, :].mean(axis=0).mean(axis=0)
    sortedVec = np.sort(connect2disp, axis=None)
    idxPercent = int(np.floor(len(sortedVec) * (100 - percentStrong) / 100))
    connect2disp = (connect2disp >= sortedVec[idxPercent]) * connect2disp

    plt.cla()

    # unused for now reactivate later?

    # mne.viz.plot_connectivity_circle(connect1disp, electrodeList, fig=f, subplot=(1, 2, 1),
    #                                  facecolor='black', textcolor='white', node_edgecolor='black',
    #                                  linewidth=1.5, colormap='hot', vmin=0, vmax=1, show=False,
    #                                  title=class1label)

    # f, ax = mne.viz.plot_connectivity_circle(connect2disp, electrodeList, fig=f, subplot=(1, 2, 2),
    #                                          facecolor='black', textcolor='white', node_edgecolor='black',
    #                                          linewidth=1.5, colormap='hot', vmin=0, vmax=1, show=False,
    #                                          title=class2label)

    f.suptitle("Strongest " + str(percentStrong) + "% of links for MSC, [" + str(fmin) + ":" + str(fmax) + "]Hz", color='white')
