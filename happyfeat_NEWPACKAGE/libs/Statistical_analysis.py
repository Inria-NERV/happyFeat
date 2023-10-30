import numpy as np
from scipy import stats

def Compute_Rsquare_Map_optimization(Power_of_trials_1,Power_of_trials_2):
    b = Power_of_trials_1.shape
    a = Power_of_trials_2.shape
    #print(a)
    #print(b)
    Rsquare_tab = np.zeros([a[1]])

    for l in range(b[1]):
        concat_tab_MI = []
        concat_tab_Rest = []
        for i in range(a[0]):
            concat_tab_MI.append(Power_of_trials_1[i,l])
            concat_tab_Rest.append(Power_of_trials_2[i,l])
            #correlation_matrix = np.corrcoef(concat_tab_MI, concat_tab_Rest)
        Sum_q = sum(concat_tab_MI)
        Sum_r = sum(concat_tab_Rest)
        n1 = len(concat_tab_MI)
        n2 = len(concat_tab_Rest)
        sumsqu1 = sum(np.multiply(concat_tab_MI,concat_tab_MI))
        sumsqu2 = sum(np.multiply(concat_tab_Rest,concat_tab_Rest))

        G=((Sum_q+Sum_r)**2)/(n1+n2)

        #correlation_xy = correlation_matrix[0,1]
        #Rsquare_tab[k,l] = correlation_xy**2
        Rsquare_tab[l] = (Sum_q**2/n1+Sum_r**2/n2-G)/(sumsqu1+sumsqu2-G)

    return Rsquare_tab


def Compute_Rsquare_Map(Power_of_trials_1,Power_of_trials_2):
    b = Power_of_trials_1.shape
    a = Power_of_trials_2.shape
    #print(a)
    #print(b)
    Rsquare_tab = np.zeros([a[1],a[2]])
    for k in range(b[1]):
        for l in range(b[2]):
            concat_tab_MI = []
            concat_tab_Rest = []
            for i in range(min(a[0], b[0])):
                concat_tab_MI.append(Power_of_trials_1[i,k,l])
                concat_tab_Rest.append(Power_of_trials_2[i,k,l])
            #correlation_matrix = np.corrcoef(concat_tab_MI, concat_tab_Rest)
            Sum_q = sum(concat_tab_MI)
            Sum_r = sum(concat_tab_Rest)
            n1 = len(concat_tab_MI)
            n2 = len(concat_tab_Rest)
            sumsqu1 = sum(np.multiply(concat_tab_MI,concat_tab_MI))
            sumsqu2 = sum(np.multiply(concat_tab_Rest,concat_tab_Rest))

            G=((Sum_q+Sum_r)**2)/(n1+n2)

            #correlation_xy = correlation_matrix[0,1]
            #Rsquare_tab[k,l] = correlation_xy**2
            Rsquare_tab[k,l] = (Sum_q**2/n1+Sum_r**2/n2-G)/(sumsqu1+sumsqu2-G)

    return Rsquare_tab

def Compute_Wilcoxon_Map_optimization(Power_of_trials_1,Power_of_trials_2):
    b = Power_of_trials_1.shape
    a = Power_of_trials_2.shape

    Wsquare_tab = np.zeros([a[1]])
    Wpsqure_tab = np.zeros([a[1]])
    for k in range(b[1]):
        concat_tab_MI = []
        concat_tab_Rest = []
        for i in range(a[0]):
            concat_tab_MI.append(Power_of_trials_1[i,k])
            concat_tab_Rest.append(Power_of_trials_2[i,k])

        s,p = stats.ranksums(concat_tab_MI,concat_tab_Rest)
        Wsquare_tab[k] = s
        Wpsqure_tab[k] = p
    return Wsquare_tab,Wpsqure_tab

def Compute_Wilcoxon_Map(Power_of_trials_1,Power_of_trials_2):
    b = Power_of_trials_1.shape
    a = Power_of_trials_2.shape

    Wsquare_tab = np.zeros([a[1],a[2]])
    Wpsqure_tab = np.zeros([a[1],a[2]])
    for k in range(b[1]):
        for l in range(b[2]):
            concat_tab_MI = []
            concat_tab_Rest = []
            for i in range(a[0]):
                concat_tab_MI.append(Power_of_trials_1[i,k,l])
                concat_tab_Rest.append(Power_of_trials_2[i,k,l])

            s,p = stats.ranksums(concat_tab_MI,concat_tab_Rest)
            Wsquare_tab[k,l] = s
            Wpsqure_tab[k,l] = p
    return Wsquare_tab,Wpsqure_tab

def Compute_Signed_Rsquare(Power_of_trials_1,Power_of_trials_2):
    b = Power_of_trials_1.shape
    a = Power_of_trials_2.shape
    #print(a)
    #print(b)
    Rsquare_tab = np.zeros([a[1],a[2]])
    Wsquare_tab = np.zeros([a[1],a[2]])
    for k in range(b[1]):
        for l in range(b[2]):
            concat_tab_MI = []
            concat_tab_Rest = []
            for i in range(a[0]):
                concat_tab_MI.append(Power_of_trials_1[i,k,l])
                concat_tab_Rest.append(Power_of_trials_2[i,k,l])
            #correlation_matrix = np.corrcoef(concat_tab_MI, concat_tab_Rest)
            Sum_q = sum(concat_tab_MI)
            Sum_r = sum(concat_tab_Rest)
            n1 = len(concat_tab_MI)
            n2 = len(concat_tab_Rest)
            sumsqu1 = sum(np.multiply(concat_tab_MI,concat_tab_MI))
            sumsqu2 = sum(np.multiply(concat_tab_Rest,concat_tab_Rest))

            G=((Sum_q+Sum_r)**2)/(n1+n2)

            #correlation_xy = correlation_matrix[0,1]
            #Rsquare_tab[k,l] = correlation_xy**2
            s,p = stats.ranksums(concat_tab_MI,concat_tab_Rest)
            
            Wsquare_tab[k,l] = s
            Rsquare_tab[k,l] = ((Sum_q**2/n1+Sum_r**2/n2-G)/(sumsqu1+sumsqu2-G))
    Wsquare_tab = Wsquare_tab/abs(Wsquare_tab)
    return Wsquare_tab*Rsquare_tab


def Compute_Signed_Rsquare_optimization(Power_of_trials_1,Power_of_trials_2):
    b = Power_of_trials_1.shape
    a = Power_of_trials_2.shape
    #print(a)
    #print(b)
    Rsquare_tab = np.zeros([a[1]])
    Wsquare_tab = np.zeros([a[1]])
    for l in range(b[1]):
        concat_tab_MI = []
        concat_tab_Rest = []
        for i in range(a[0]):
            concat_tab_MI.append(Power_of_trials_1[i,l])
            concat_tab_Rest.append(Power_of_trials_2[i,l])
            #correlation_matrix = np.corrcoef(concat_tab_MI, concat_tab_Rest)
        Sum_q = sum(concat_tab_MI)
        Sum_r = sum(concat_tab_Rest)
        n1 = len(concat_tab_MI)
        n2 = len(concat_tab_Rest)
        sumsqu1 = sum(np.multiply(concat_tab_MI,concat_tab_MI))
        sumsqu2 = sum(np.multiply(concat_tab_Rest,concat_tab_Rest))

        G=((Sum_q+Sum_r)**2)/(n1+n2)
        s,p = stats.ranksums(concat_tab_MI,concat_tab_Rest)
        #correlation_xy = correlation_matrix[0,1]
        #Rsquare_tab[k,l] = correlation_xy**2
        Rsquare_tab[l] = np.sign(s)*((Sum_q**2/n1+Sum_r**2/n2-G)/(sumsqu1+sumsqu2-G))
        Wsquare_tab[l] = s
    Wsquare_tab = Wsquare_tab/abs(Wsquare_tab)
    return Wsquare_tab*Rsquare_tab
