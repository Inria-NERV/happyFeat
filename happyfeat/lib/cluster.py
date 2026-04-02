import mne
import pandas as pd
import numpy as np

# Perform clustering using result structure from happyfeat
# ("Feature" class)
def doClusteringFull(result, n_perm=5000, p_threshold=0.05, sfreq=500, fmin=0, fmax=250, verbose=False):

    if len(result.power_cond1) > 0 and len(result.power_cond2) > 0:
        cond1_corr = np.nan_to_num(result.power_cond1[:, :, fmin:fmax])
        cond2_corr = np.nan_to_num(result.power_cond2[:, :, fmin:fmax])

        T_obs, clusters, p_vals, info = cluster_perm_spatiofreq(
            cond1=cond1_corr, cond2=cond2_corr,
            eeg_ch_names=result.electrodes_final,
            n_perm=n_perm, sfreq=sfreq, tail=0,
            montageStr="standard_1020", verbose=verbose
        )

        clusterMask = filter_map(T_obs, p_vals, p_threshold, clusters)

        print("clusterMask size " + str(np.shape(clusterMask)))

        tempRsquare = np.where(clusterMask, result.Rsquare[:, :np.shape(clusterMask)[1]], np.nan)

    return tempRsquare, clusterMask

def doClustering(result, n_perm=5000, p_threshold=0.05, sfreq=500, fmin=0, fmax=250, verbose=False):

    if len(result.power_cond1) > 0 and len(result.power_cond2) > 0:
        cond1_corr = np.nan_to_num(result.power_cond1[:, :, fmin:fmax])
        cond2_corr = np.nan_to_num(result.power_cond2[:, :, fmin:fmax])

        T_obs, clusters, p_vals, info = cluster_perm_spatiofreq(
            cond1=cond1_corr, cond2=cond2_corr,
            eeg_ch_names=result.electrodes_final,
            n_perm=n_perm, sfreq=sfreq, tail=0,
            montageStr="standard_1020", verbose=verbose
        )

    return T_obs, p_vals, p_threshold, clusters

def filter_map(metric_map, p_map, threshold, clusters=None):
    SigMask = np.zeros_like(metric_map, dtype=bool)
    if clusters is None:
        SigMask = p_map < threshold
    else:
        print("==========filter_map")
        for clu, p in zip(clusters, p_map):
            if p < threshold:
                print(np.where(clu))
                SigMask[clu] = True
    return SigMask

def pvalmap(metric_map, p_map, threshold, clusters=None):
    pvalmap = np.zeros_like(metric_map, dtype=bool)
    if clusters is None:
        SigMask = p_map < threshold
    else:
        for clu, p in zip(clusters, p_map):
            pvalmap[clu] = p
    return pvalmap

def cluster_perm_spatiofreq(cond1, cond2, eeg_ch_names, montageStr="standard_1020",
                            n_perm=2000, sfreq=500, tail=0, verbose=False):
    """
    MI, REST: shape (n_trials, n_ch, n_freq)
    tail=0 -> two-sided ; tail=1 -> MI>REST ; tail=-1 -> MI<REST
    """

    # adjacency, info = build_spatiofreq_adjacency(eeg_ch_names, n_freq,  montageStr=montageStr, sfreq=sfreq)
    # -> only spatial if uniform along freq and max_step provided
    adjacency, info = build_spatial_adjacency(eeg_ch_names, montageStr=montageStr, sfreq=sfreq)

    # PS: mne : data organized in the form (observations × time × space), (observations × frequencies × space),
    # or optionally (observations × time × frequencies × space).

    cond1 = cond1.transpose(0, 2, 1)  # (trials, freq, ch)
    cond2 = cond2.transpose(0, 2, 1)

    print("min/max of corr1 :" + str(np.min(cond1)) + " " + str(np.max(cond1)))
    print("cond1_corr size " + str(np.shape(cond1)))

    D = cond1 - cond2  # (trials, ch, freq)

    print("min/max of D :" + str(np.min(D)) + " " + str(np.max(D)))
    print("D size " + str(np.shape(D)))

    T_obs, clusters, p_values, H0 = mne.stats.spatio_temporal_cluster_1samp_test(
        D,
        adjacency=adjacency,  # spatial only
        max_step=1,  # adjacency across neighboring freqs ~ 1 bin
        n_permutations=n_perm,
        n_jobs=4,
        tail=tail,
        out_type="mask",
        verbose=verbose
    )  ## -> check_disjoint=True if freq high

    # Remettre T_obs en (ch, freq)
    T_obs = T_obs.T
    clusters_2d = [c.T for c in clusters]

    return T_obs, clusters_2d, p_values, info


def build_spatial_adjacency(eeg_ch_names, montageStr="standard_1020", customMontage=None, sfreq=500):

    # ---------- Montage ----------
    if montageStr == "custom":

        df = pd.read_csv(customMontage)
        ch_names = df.name.to_list()
        pos = df[['x', 'y', 'z']].values
        dig_ch_pos = dict(zip(ch_names, pos))

        if set(['Nz', 'LPA', 'RPA']).issubset(ch_names):

            idx_Nz = ch_names.index('Nz')
            idx_LPA = ch_names.index('LPA')
            idx_RPA = ch_names.index('RPA')

            montage_inter = mne.channels.make_dig_montage(
                ch_pos=dig_ch_pos,
                nasion=pos[idx_Nz],
                lpa=pos[idx_LPA],
                rpa=pos[idx_RPA]
            )

            ind = [i for i, ch in enumerate(montage_inter.ch_names)
                   if ch in eeg_ch_names]

            montage = montage_inter.copy()
            montage.ch_names = [montage_inter.ch_names[x] for x in ind]

            kept_channel_info = [montage_inter.dig[x + 3] for x in ind]
            montage.dig = montage_inter.dig[0:3] + kept_channel_info

        else:

            montage_inter = mne.channels.make_dig_montage(ch_pos=dig_ch_pos)
            selected_channels = [ch for ch in eeg_ch_names if ch in montage_inter.ch_names]

            if len(selected_channels) != len(eeg_ch_names):
                missing = [ch for ch in eeg_ch_names if ch not in montage_inter.ch_names]
                raise ValueError(f"Channels missing from montage: {missing}")

            ind = [montage_inter.ch_names.index(ch) for ch in selected_channels]

            montage = montage_inter.copy()
            montage.ch_names = [montage_inter.ch_names[x] for x in ind]
            montage.dig = [montage_inter.dig[x] for x in ind]

    else:

        montage_inter = mne.channels.make_standard_montage(montageStr)

        ind = [i for i, ch in enumerate(montage_inter.ch_names)
               if ch in eeg_ch_names]

        montage = montage_inter.copy()
        montage.ch_names = [montage_inter.ch_names[x] for x in ind]

        kept_channel_info = [montage_inter.dig[x + 3] for x in ind]
        montage.dig = montage_inter.dig[0:3] + kept_channel_info

    # ---------- Info MNE ----------
    info = mne.create_info(
        ch_names=montage.ch_names,
        sfreq=sfreq,
        ch_types="eeg"
    )

    info.set_montage(montage)

    # ---------- Adjacency spatiale ----------
    ch_adjacency, ch_names_adj = mne.channels.find_ch_adjacency(
        info,
        ch_type="eeg"
    )

    return ch_adjacency, info



