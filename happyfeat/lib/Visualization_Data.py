from happyfeat.lib.Statistical_analysis import *
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from matplotlib import cm
from mne.defaults import _EXTRAPOLATE_DEFAULT, _BORDER_DEFAULT

import mne
from mne.io.meas_info import Info
from mne.viz import topomap

import pandas as pd

def add_colorbar(ax, im, cmap, side="right", pad=.05, title=None,
                 format=None, size="5%"):
    """Add a colorbar to an axis."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    divider = make_axes_locatable(ax)
    cax = divider.append_axes(side, size=size, pad=pad)
    cbar = plt.colorbar(im, cax=cax, format=format)

    return cbar, cax

def topo_plot(Rsquare, title, montageStr, customMontage, electrodes, freqMin, freqMax, fres, fs, scaleColormap, Stat_method):
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
            montage.dig = [montage_inter.dig[x + 3] for x in ind]

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
                    sizer[i] = Rsquare[:, freqMin][j]
    else:
        freq = str(freqMin) + ":" + str(freqMax)
        for i in range(n_channels):
            for j in range(len(electrodes)):
                if montage.ch_names[i] == electrodes[j]:
                    sizer[i] = Rsquare[:, freqMin:freqMax][j].mean()

    vmin = None
    vmax = 1
    if scaleColormap:
        vmax = None

    plot_topomap_data_viz(title, sizer, fake_evoked.info, sensors=False, names=montage.ch_names, show_names=True,
                          res=500, mask_params=dict(marker='', markerfacecolor='w', markeredgecolor='k', linewidth=0,
                                                    markersize=0), contours=0, image_interp='cubic', show=True,
                          extrapolate='head', cmap='jet', freq=freq, vmin=vmin, vmax=vmax, Stat_method=Stat_method)

def plot_topomap_data_viz(title, data, pos, vmin=None, vmax=None, cmap=None, sensors=True,
                          res=64, axes=None, names=None, show_names=False, mask=None,
                          mask_params=None, outlines='head',
                          contours=6, image_interp='cubic', show=True,
                          onselect=None, extrapolate=_EXTRAPOLATE_DEFAULT,
                          sphere=None, border=_BORDER_DEFAULT,
                          ch_type='eeg', freq='10', Stat_method='R_square signed'):
    """Plot a topographic map as image.

    Parameters
    ----------
    data : array, shape (n_chan,)
        The data values to plot.
    pos : array, shape (n_chan, 2) | instance of Info
        Location information for the data points(/channels).
        If an array, for each data point, the x and y coordinates.
        If an Info object, it must contain only one data type and
        exactly ``len(data)`` data channels, and the x/y coordinates will
        be inferred from this Info object.
    vmin : float | callable | None
        The value specifying the lower bound of the color range.
        If None, and vmax is None, -vmax is used. Else np.min(data).
        If callable, the output equals vmin(data). Defaults to None.
    vmax : float | callable | None
        The value specifying the upper bound of the color range.
        If None, the maximum absolute value is used. If callable, the output
        equals vmax(data). Defaults to None.
    cmap : matplotlib colormap | None
        Colormap to use. If None, 'Reds' is used for all positive data,
        otherwise defaults to 'RdBu_r'.
    sensors : bool | str
        Add markers for sensor locations to the plot. Accepts matplotlib plot
        format string (e.g., 'r+' for red plusses). If True (default), circles
        will be used.
    res : int
        The resolution of the topomap image (n pixels along each side).
    axes : instance of Axes | None
        The axes to plot to. If None, the current axes will be used.
    names : list | None
        List of channel names. If None, channel names are not plotted.
    %(topomap_show_names)s
        If ``True``, a list of names must be provided (see ``names`` keyword).
    mask : ndarray of bool, shape (n_channels, n_times) | None
        The channels to be marked as significant at a given time point.
        Indices set to ``True`` will be considered. Defaults to None.
    mask_params : dict | None
        Additional plotting parameters for plotting significant sensors.
        Default (None) equals::

           dict(marker='o', markerfacecolor='w', markeredgecolor='k',
                linewidth=0, markersize=4)
    %(topomap_outlines)s
    contours : int | array of float
        The number of contour lines to draw. If 0, no contours will be drawn.
        If an array, the values represent the levels for the contours. The
        values are in µV for EEG, fT for magnetometers and fT/m for
        gradiometers. Defaults to 6.
    image_interp : str
        The image interpolation to be used. All matplotlib options are
        accepted.
    show : bool
        Show figure if True.
    onselect : callable | None
        Handle for a function that is called when the user selects a set of
        channels by rectangle selection (matplotlib ``RectangleSelector``). If
        None interactive selection is disabled. Defaults to None.
    %(topomap_extrapolate)s

        .. versionadded:: 0.18
    %(topomap_sphere)s
    %(topomap_border)s
    %(topomap_ch_type)s

    Returns
    -------
    im : matplotlib.image.AxesImage
        The interpolated data.
    cn : matplotlib.contour.ContourSet
        The fieldlines.
    """
    sphere = topomap._check_sphere(sphere)
    return _plot_topomap_test(title, data, pos, vmin, vmax, cmap, sensors, res, axes,
                              names, show_names, mask, mask_params, outlines,
                              contours, image_interp, show,
                              onselect, extrapolate, sphere=sphere, border=border,
                              ch_type=ch_type, freq=freq, Stat_method=Stat_method)[:2]


def _plot_topomap_test(title, data, pos, vmin=None, vmax=None, cmap=None, sensors=True, res=64, axes=None, names=None,
                       show_names=False, mask=None, mask_params=None, outlines='head', contours=6,
                       image_interp='cubic', show=True, onselect=None, extrapolate=_EXTRAPOLATE_DEFAULT, sphere=None,
                       border=_BORDER_DEFAULT, ch_type='eeg', freq='10', Stat_method='R square signed'):

    data = np.asarray(data)

    if isinstance(pos, Info):  # infer pos from Info object
        picks = topomap._pick_data_channels(pos, exclude=())  # pick only data channels
        pos = topomap.pick_info(pos, picks)

        # check if there is only 1 channel type, and n_chans matches the data
        ch_type = topomap._get_channel_types(pos, unique=True)
        info_help = ("Pick Info with e.g. mne.pick_info and "
                     "mne.io.pick.channel_indices_by_type.")
        if len(ch_type) > 1:
            raise ValueError("Multiple channel types in Info structure. " +
                             info_help)
        elif len(pos["chs"]) != data.shape[0]:
            raise ValueError("Number of channels in the Info object (%s) and "
                             "the data array (%s) do not match. "
                             % (len(pos['chs']), data.shape[0]) + info_help)
        else:
            ch_type = ch_type.pop()

        if any(type_ in ch_type for type_ in ('planar', 'grad')):
            # deal with grad pairs
            picks = topomap._pair_grad_sensors(pos, topomap_coords=False)
            pos = topomap._find_topomap_coords(pos, picks=picks[::2], sphere=sphere, ignore_overlap=True)
            data, _ = topomap._merge_ch_data(data[picks], ch_type, [])
            data = data.reshape(-1)
        else:
            picks = list(range(data.shape[0]))
            pos = topomap._find_topomap_coords(pos, picks=picks, sphere=sphere, ignore_overlap=True)

    extrapolate = topomap._check_extrapolate(extrapolate, ch_type)
    if data.ndim > 1:
        raise ValueError("Data needs to be array of shape (n_sensors,); got "
                         "shape %s." % str(data.shape))

    # Give a helpful error message for common mistakes regarding the position
    # matrix.
    pos_help = ("Electrode positions should be specified as a 2D array with "
                "shape (n_channels, 2). Each row in this matrix contains the "
                "(x, y) position of an electrode.")
    if pos.ndim != 2:
        error = ("{ndim}D array supplied as electrode positions, where a 2D "
                 "array was expected").format(ndim=pos.ndim)
        raise ValueError(error + " " + pos_help)
    elif pos.shape[1] == 3:
        error = ("The supplied electrode positions matrix contains 3 columns. "
                 "Are you trying to specify XYZ coordinates? Perhaps the "
                 "mne.channels.create_eeg_layout function is useful for you.")
        raise ValueError(error + " " + pos_help)
    # No error is raised in case of pos.shape[1] == 4. In this case, it is
    # assumed the position matrix contains both (x, y) and (width, height)
    # values, such as Layout.pos.
    elif pos.shape[1] == 1 or pos.shape[1] > 4:
        raise ValueError(pos_help)
    pos = pos[:, :2]

    if len(data) != len(pos):
        raise ValueError("Data and pos need to be of same length. Got data of "
                         "length %s, pos of length %s" % (len(data), len(pos)))

    norm = min(data) >= 0
    vmin, vmax = topomap._setup_vmin_vmax(data, vmin, vmax, norm)

    outlines = topomap._make_head_outlines(sphere, pos, outlines, (0., 0.))
    assert isinstance(outlines, dict)

    ax = axes if axes else plt.gca()
    topomap._prepare_topomap(pos, ax)

    mask_params = topomap._handle_default('mask_params', mask_params)

    # find mask limits
    extent, Xi, Yi, interp = topomap._setup_interp(
        pos, res, image_interp, extrapolate, outlines, border)
    interp.set_values(data)
    Zi = interp.set_locations(Xi, Yi)()

    # plot outline
    patch_ = topomap._get_patch(outlines, extrapolate, interp, ax)

    # plot interpolated map
    im = ax.imshow(Zi, cmap=cmap, vmin=vmin, vmax=vmax, origin='lower',
                   aspect='equal', extent=extent)
    cbar, cax = add_colorbar(ax, im, cmap, side="right", pad=.1, title=None,
                             format=None, size="5%")
    cbar.set_label('R^2 value', rotation=270, labelpad=15)
    ax.set_title(title + freq + ' Hz', fontsize='large')
    # gh-1432 had a workaround for no contours here, but we'll remove it
    # because mpl has probably fixed it
    linewidth = mask_params['markeredgewidth']
    cont = True
    if isinstance(contours, (np.ndarray, list)):
        pass
    elif contours == 0 or ((Zi == Zi[0, 0]) | np.isnan(Zi)).all():
        cont = None  # can't make contours for constant-valued functions
    if cont:
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('ignore')
            cont = ax.contour(Xi, Yi, Zi, contours, colors='k',
                              linewidths=linewidth / 2.)

    if patch_ is not None:
        im.set_clip_path(patch_)
        if cont is not None:
            for col in cont.collections:
                col.set_clip_path(patch_)

    pos_x, pos_y = pos.T
    if sensors is not False and mask is None:
        topomap._topomap_plot_sensors(pos_x, pos_y, sensors=sensors, ax=ax)
    elif sensors and mask is not None:
        idx = np.where(mask)[0]
        ax.plot(pos_x[idx], pos_y[idx], **mask_params)
        idx = np.where(~mask)[0]
        topomap._topomap_plot_sensors(pos_x[idx], pos_y[idx], sensors=sensors, ax=ax)
    elif not sensors and mask is not None:
        idx = np.where(mask)[0]
        ax.plot(pos_x[idx], pos_y[idx], **mask_params)

    if isinstance(outlines, dict):
        topomap._draw_outlines(ax, outlines)

    if show_names:
        if names is None:
            raise ValueError("To show names, a list of names must be provided"
                             " (see `names` keyword).")
        if show_names is True:
            def _show_names(x):
                return x
        else:
            _show_names = show_names
        show_idx = np.arange(len(names)) if mask is None else np.where(mask)[0]
        for ii, (p, ch_id) in enumerate(zip(pos, names)):
            if ii not in show_idx:
                continue
            ch_id = _show_names(ch_id)
            ax.text(p[0], p[1], ch_id, horizontalalignment='center',
                    verticalalignment='center', size='small', fontweight='bold')

    plt.subplots_adjust(top=.95)

    if onselect is not None:
        lim = ax.dataLim
        x0, y0, width, height = lim.x0, lim.y0, lim.width, lim.height
        ax.RS = RectangleSelector(ax, onselect=onselect)
        ax.set(xlim=[x0, x0 + width], ylim=[y0, y0 + height])

    # topomap.plt_show(show)
    return im, cont, interp


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

    frequence = []

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
            frequence.append(str(round(i)))
        else:
            frequence.append('')
    cm.get_cmap('jet')
    # plt.jet()
    ax.tick_params(axis='both', which='both', length=0)
    cbar = plt.colorbar()
    cbar.set_label('ERD/ERS', rotation=270, labelpad=10)
    plt.yticks(range(len(freqs[index_fmin:index_fmax + 1])), frequence, fontsize=7)

    plt.xticks(range(len(time)), time_seres, fontsize=7)
    plt.xlabel(' Time (s)', fontdict=font)
    plt.ylabel('Frequency (Hz)', fontdict=font)

    # plt.show()

def plot_psd(Power_class1, Power_class2, freqs, channel, channel_array, each_point, fmin, fmax, fres, class1label,
             class2label, title):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }

    fig, ax = plt.subplots()
    frequence = []
    Aver_class2 = 10 * np.log10(Power_class2[:, channel, :])
    Aver_class2 = Aver_class2.mean(0)
    STD_class2 = 10 * np.log10(Power_class2[:, channel, :])
    STD_class2 = STD_class2.std(0)

    Aver_class1 = 10 * np.log10(Power_class1[:, channel, :])
    Aver_class1 = Aver_class1.mean(0)
    STD_class1 = 10 * np.log10(Power_class1[:, channel, :])
    STD_class1 = STD_class1.std(0)
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i

    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i
    # plt.plot(Aver_class2,freqs,Aver_class1,freqs)
    # index_fmin = np.where(np.abs(freqs-fmin)<0.00001)
    # index_fmax = np.where(np.abs(freqs-fmax)<0.00001)
    # print(index_fmin)
    Selected_class2 = (Aver_class2[index_fmin:index_fmax])
    Selected_class1 = (Aver_class1[index_fmin:index_fmax])

    Selected_class2_STD = (STD_class2[index_fmin:index_fmax] / Power_class2.shape[0])
    Selected_class1_STD = (STD_class1[index_fmin:index_fmax] / Power_class2.shape[0])

    plt.plot(freqs[index_fmin:index_fmax], Selected_class2, label=class2label, color='blue')

    plt.fill_between(freqs[index_fmin:index_fmax], Selected_class2 - Selected_class2_STD, Selected_class2 + Selected_class2_STD,
                     color='blue', alpha=0.3)
    plt.plot(freqs[index_fmin:index_fmax], Selected_class1, label=class1label, color='red')
    plt.fill_between(freqs[index_fmin:index_fmax], Selected_class1 - Selected_class1_STD,
                     Selected_class1 + Selected_class1_STD,
                     color='red', alpha=0.3)
    sizing = round(len(freqs[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freqs[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequence.append(str(round(i)))
        else:
            frequence.append('')
    ax.tick_params(axis='both', which='both', length=0)

    plt.title(title+'Sensor: ' + channel_array[channel], fontsize='large')
    # plt.xticks(range(len(freqs[index_fmin:(index_fmax + 1)])), frequence, fontsize=12)
    plt.xlabel(' Frequency (Hz)', fontdict=font)
    plt.ylabel('Power spectrum (db)', fontdict=font)
    plt.margins(x=0)
    # ax.set_xticks(np.arange(fmin, fmax, sizing))
    ax.grid(axis='x')
    # plt.axis('square')

    plt.legend()
    # plt.show()


def plot_psd_r2(Power_class1, Power_class2, Rsquare, freqs, channel, channel_array, each_point, fmin, fmax, fres, class1label,
             class2label, title):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }

    fig, ax = plt.subplots()
    frequence = []
    Aver_class2 = 10 * np.log10(Power_class2[:, channel, :])
    Aver_class2 = Aver_class2.mean(0)
    STD_class2 = 10 * np.log10(Power_class2[:, channel, :])
    STD_class2 = STD_class2.std(0)

    Aver_class1 = 10 * np.log10(Power_class1[:, channel, :])
    Aver_class1 = Aver_class1.mean(0)
    STD_class1 = 10 * np.log10(Power_class1[:, channel, :])
    STD_class1 = STD_class1.std(0)
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i

    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i
    # plt.plot(Aver_class2,freqs,Aver_class1,freqs)
    # index_fmin = np.where(np.abs(freqs-fmin)<0.00001)
    # index_fmax = np.where(np.abs(freqs-fmax)<0.00001)
    # print(index_fmin)
    Selected_class2 = (Aver_class2[index_fmin:index_fmax])
    Selected_class1 = (Aver_class1[index_fmin:index_fmax])

    Selected_class2_STD = (STD_class2[index_fmin:index_fmax] / Power_class2.shape[0])
    Selected_class1_STD = (STD_class1[index_fmin:index_fmax] / Power_class2.shape[0])

    plt.plot(freqs[index_fmin:index_fmax], Selected_class2, label=class2label, color='blue')

    plt.fill_between(freqs[index_fmin:index_fmax], Selected_class2 - Selected_class2_STD, Selected_class2 + Selected_class2_STD,
                     color='blue', alpha=0.3)
    plt.plot(freqs[index_fmin:index_fmax], Selected_class1, label=class1label, color='red')
    plt.fill_between(freqs[index_fmin:index_fmax], Selected_class1 - Selected_class1_STD,
                     Selected_class1 + Selected_class1_STD,
                     color='red', alpha=0.3)

    classes_max_value = max(max(Selected_class1), max(Selected_class2))
    selected_Rsquare = Rsquare[channel, index_fmin:index_fmax] * classes_max_value
    plt.plot(freqs[index_fmin:index_fmax], selected_Rsquare, label="r2", color='black')

    sizing = round(len(freqs[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freqs[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequence.append(str(round(i)))
        else:
            frequence.append('')
    ax.tick_params(axis='both', which='both', length=0)

    plt.title(title+'Sensor: ' + channel_array[channel], fontsize='large')
    # plt.xticks(range(len(freqs[index_fmin:(index_fmax + 1)])), frequence, fontsize=12)
    plt.xlabel(' Frequency (Hz)', fontdict=font)
    plt.ylabel('Power spectrum (db)', fontdict=font)
    plt.margins(x=0)
    # ax.set_xticks(np.arange(fmin, fmax, sizing))
    ax.grid(axis='x')
    # plt.axis('square')

    plt.legend()
    # plt.show()

def plot_metric(Power_class1, Power_class2, freqs, channel, channel_array, each_point, fmin, fmax, fres, class1label,
             class2label, metricLabel, title):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }

    fig, ax = plt.subplots()
    frequence = []
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i

    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i

    Aver_class1 = Power_class1[:, channel, :].mean(0)
    STD_class1 = Power_class1[:, channel, :].mean(0)
    Selected_class1 = (Aver_class1[index_fmin:index_fmax])
    Selected_class1_STD = (STD_class1[index_fmin:index_fmax] / Power_class2.shape[0])
    Aver_class2 = Power_class2[:, channel, :].mean(0)
    STD_class2 = Power_class2[:, channel, :].mean(0)
    Selected_class2 = (Aver_class2[index_fmin:index_fmax])
    Selected_class2_STD = (STD_class2[index_fmin:index_fmax] / Power_class2.shape[0])

    plt.plot(freqs[index_fmin:index_fmax], Selected_class2, label=class2label, color='blue')

    # plt.fill_between(freqs[index_fmin:index_fmax], Selected_class2 - Selected_class2_STD, Selected_class2 + Selected_class2_STD,
    #                  color='blue', alpha=0.3)
    plt.plot(freqs[index_fmin:index_fmax], Selected_class1, label=class1label, color='red')
    # plt.fill_between(freqs[index_fmin:index_fmax], Selected_class1 - Selected_class1_STD,
    #                  Selected_class1 + Selected_class1_STD,
    #                  color='red', alpha=0.3)

    sizing = round(len(freqs[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freqs[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequence.append(str(round(i)))
        else:
            frequence.append('')
    ax.tick_params(axis='both', which='both', length=0)

    plt.title(title+'Sensor: ' + channel_array[channel], fontsize='large')
    # plt.xticks(range(len(freqs[index_fmin:(index_fmax + 1)])), frequence, fontsize=12)
    plt.xlabel(' Frequency (Hz)', fontdict=font)
    plt.ylabel(str(metricLabel + ' per frequency'), fontdict=font)
    plt.margins(x=0)
    # ax.set_xticks(np.arange(fmin, fmax, sizing))
    ax.grid(axis='x')
    # plt.axis('square')

    plt.legend()
    # plt.show()

def plot_metric2(Power_class1, Power_class2, Rsquare, freqs, channel, channel_array, each_point, fmin, fmax, fres, class1label,
             class2label, metricLabel, title):
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14,
            }

    fig, ax = plt.subplots()
    frequence = []
    for i in range(len(freqs)):
        if freqs[i] == fmin:
            index_fmin = i

    for i in range(len(freqs)):
        if freqs[i] == fmax:
            index_fmax = i

    Aver_class1 = Power_class1[:, channel, :].mean(0)
    STD_class1 = Power_class1[:, channel, :].mean(0)
    Selected_class1 = (Aver_class1[index_fmin:index_fmax])
    Selected_class1_STD = (STD_class1[index_fmin:index_fmax] / Power_class2.shape[0])
    Aver_class2 = Power_class2[:, channel, :].mean(0)
    STD_class2 = Power_class2[:, channel, :].mean(0)
    Selected_class2 = (Aver_class2[index_fmin:index_fmax])
    Selected_class2_STD = (STD_class2[index_fmin:index_fmax] / Power_class2.shape[0])

    plt.plot(freqs[index_fmin:index_fmax], Selected_class2, label=class2label, color='blue')

    # plt.fill_between(freqs[index_fmin:index_fmax], Selected_class2 - Selected_class2_STD, Selected_class2 + Selected_class2_STD,
    #                  color='blue', alpha=0.3)
    plt.plot(freqs[index_fmin:index_fmax], Selected_class1, label=class1label, color='red')
    # plt.fill_between(freqs[index_fmin:index_fmax], Selected_class1 - Selected_class1_STD,
    #                  Selected_class1 + Selected_class1_STD,
    #                  color='red', alpha=0.3)

    selected_Rsquare = Rsquare[channel, index_fmin:index_fmax]
    # test scaling for r2
    if max(Selected_class1) > 1.0:
        factor = max(Selected_class1) / max(selected_Rsquare)
        selected_Rsquare = selected_Rsquare * factor

    plt.plot(freqs[index_fmin:index_fmax], selected_Rsquare, label="r2", color='black')

    sizing = round(len(freqs[index_fmin:(index_fmax + 1)]) / (each_point * 1 / fres))
    for i in freqs[index_fmin:(index_fmax + 1)]:
        if i % (round(sizing * 1 / fres)) == 0:
            frequence.append(str(round(i)))
        else:
            frequence.append('')
    ax.tick_params(axis='both', which='both', length=0)

    plt.title(title+'Sensor: ' + channel_array[channel], fontsize='large')
    # plt.xticks(range(len(freqs[index_fmin:(index_fmax + 1)])), frequence, fontsize=12)
    plt.xlabel(' Frequency (Hz)', fontdict=font)
    plt.ylabel(str(metricLabel + ' per frequency'), fontdict=font)
    plt.margins(x=0)
    # ax.set_xticks(np.arange(fmin, fmax, sizing))
    ax.grid(axis='x')
    # plt.axis('square')

    plt.legend()
    # plt.show()

def plot_Rsquare_calcul_welch(Rsquare, channel_array, freq, smoothing, fres, each_point, fmin, fmax, colormapScale, title):
    fig, ax = plt.subplots()
    font = {'family': 'serif',
            'color': 'black',
            'weight': 'normal',
            'size': 14}
    frequence = []

    for i in range(len(freq)):
        if freq[i] == fmin:
            index_fmin = i

    for i in range(len(freq)):
        if freq[i] == fmax:
            index_fmax = i
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
            frequence.append(str(round(i)))
        else:
            frequence.append('')

    if smoothing:
        plt.xlim(0, 80)
    else:
        # plt.xticks(range(0,len(freq)-1,round(2/fres)),freq_real)
        # plt.xlim(0,round(70/fres))
        ax.tick_params(axis='both', which='both', length=0)
        plt.xticks(range(len(freq[index_fmin:index_fmax + 1])), frequence, fontsize=10)
        # plt.xlim(0,round(72/fres))

    plt.xlabel('Frequency (Hz)', fontdict=font)
    plt.ylabel('Sensors', fontdict=font)

    # Major ticks
    ax.set_xticks(np.arange(0, len(freq[index_fmin:index_fmax + 1]), 1))
    ax.set_yticks(np.arange(0, len(channel_array), 1))

    # Labels for major ticks
    ax.set_xticklabels(frequence)
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

def Reorder_plusplus(Rsquare, electrodes_orig, powerLeft, powerRight, timefreqLeft, timefreqRight):
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
                    break

    print(index_elec)

    Rsquare_final = np.zeros([Rsquare.shape[0], Rsquare.shape[1]])
    print(powerLeft.shape)
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

    return Rsquare_final, electrode_final, powerLeft_final, powerRight_final, timefreqLeftfinal, timefreqRightfinal

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

def Reorder_custom_plus(Rsquare, customPath, electrodes_orig, powerLeft, powerRight, timefreqLeft, timefreqRight):

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

    return Rsquare_final, electrode_final, powerLeft_final, powerRight_final, timefreqLeftfinal, timefreqRightfinal



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
    frequence = []

    for i in range(len(freq)):
        if freq[i] == fmin:
            index_fmin = i

    for i in range(len(freq)):
        if freq[i] == fmax:
            index_fmax = i
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
            frequence.append(str(round(i)))
        else:
            frequence.append('')

    if smoothing:
        plt.xlim(0, 80)
    else:
        # plt.xticks(range(0,len(freq)-1,round(2/fres)),freq_real)
        # plt.xlim(0,round(70/fres))
        ax.tick_params(axis='both', which='both', length=0)
        plt.xticks(range(len(freq[index_fmin:index_fmax + 1])), frequence, fontsize=10)
        # plt.xlim(0,round(72/fres))
    plt.xlabel('Frequency (Hz)', fontdict=font)
    plt.ylabel('Sensors', fontdict=font)

    # Major ticks
    ax.set_xticks(np.arange(0, len(freq[index_fmin:index_fmax + 1]), 1))
    ax.set_yticks(np.arange(0, len(channel_array), 1))

    # Labels for major ticks
    ax.set_xticklabels(frequence)
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
    frequence = []

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
            frequence.append(str(round(i)))
        else:
            frequence.append('')
    cm.get_cmap('jet')
    # plt.jet()
    ax.tick_params(axis='both', which='both', length=0)
    cbar = plt.colorbar()
    cbar.set_label('Signed R^2', rotation=270, labelpad=10)
    plt.yticks(range(len(freqs[index_fmin:index_fmax + 1])), frequence, fontsize=7)

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
    frequence = []
    avg_class1 = connect1[:, :, chan1idx, chan2idx].mean(axis=0)
    avg_class2 = connect2[:, :, chan1idx, chan2idx].mean(axis=0)

    # Only plot half of the spectrum, since it's mirrored
    sizeSpectrum = int(np.floor((len(avg_class1)+1) / 2))

    plt.plot(avg_class1[0:sizeSpectrum], label=class1label, color='blue')
    plt.plot(avg_class2[0:sizeSpectrum], label=class2label, color='red')
    ax.tick_params(axis='both', which='both', length=0)

    plt.title('Connectivity btw. ' + electrodeList[chan1idx] + ' and ' + electrodeList[chan2idx], fontsize='large')
    # plt.xticks(range(len(freqs[index_fmin:(index_fmax + 1)])), frequence, fontsize=12)
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
    mne.viz.plot_connectivity_circle(connect1disp, electrodeList, fig=f, subplot=(1, 2, 1),
                                       facecolor='black', textcolor='white', node_edgecolor='black',
                                       linewidth=1.5, colormap='hot', vmin=0, vmax=1, show=False,
                                       title=class1label)

    f, ax = mne.viz.plot_connectivity_circle(connect2disp, electrodeList, fig=f, subplot=(1, 2, 2),
                                       facecolor='black', textcolor='white', node_edgecolor='black',
                                       linewidth=1.5, colormap='hot', vmin=0, vmax=1, show=False,
                                       title=class2label)

    f.suptitle("Strongest " + str(percentStrong) + "% of links for MSC, [" + str(fmin) + ":" + str(fmax) + "]Hz", color='white')
