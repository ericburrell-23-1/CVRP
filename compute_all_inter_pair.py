import numpy as np
from timeit import default_timer as timer


def powerset(s):
    x = len(s)

    masks = [1 << i for i in range(x)]
    for i in range(1 << x):
        yield [ss for mask, ss in zip(masks, s) if i & mask]


def compute_all_inter_pair(LA_neigh, dist_mat_orig, dist_2_depot, NumLA, AllCust, capacity, demand):

    # let all_inter be the union (over all u\in N) of the power sets of LA_neighbors of u
    timeBef = []
    start_time = timer()

    dist_mat = dist_mat_orig.copy()
    for u in AllCust:
        dist_mat[-1, u] = dist_2_depot[u]
        dist_mat[u, -2] = dist_2_depot[u]
    timeBef.append(timer()-start_time)
    print('step 0')
    start_time = timer()

    all_inter = set([])
    all_inter_u = dict()
    for u in AllCust:
        this_all_inter = powerset(LA_neigh[u])
        all_inter_u[u] = set()
        for s in this_all_inter:
            s = sorted(s)
            my_new_el = tuple(s)
            all_inter.add(my_new_el)
            all_inter_u[u].add(my_new_el)
    timeBef.append(timer()-start_time)
    print('step 1')
    start_time = timer()

    dictNhat2DemTot = dict()
    for inter in all_inter:
        tot_dem = 0
        for w in inter:
            tot_dem = tot_dem+demand[w]
        dictNhat2DemTot[inter] = tot_dem
    timeBef.append(timer()-start_time)
    print('step 2')
    start_time = timer()

    # let dict_all_inter_by_size be a mapping from number of eleemtns of a term in all_inter to all_inter of that size
    dict_all_inter_by_size = dict()
    dict_all_inter_pair_by_size = dict()
    for i in range(0, NumLA+1):
        dict_all_inter_by_size[i] = set([])
        dict_all_inter_pair_by_size[i] = set()  # dict()
    timeBef.append(timer()-start_time)
    print('step 3')
    start_time = timer()

    # dict_inter_2_comp be a mappping from  all_inter to all terms where the first_last customer are selected
    dict_inter_2_comp = dict()
    # dict_all_inter_pair_by_size be a mapping produced by conditioning on pair

    counter = 0
    for Nhat_tmp in all_inter:
        counter = counter+1
        Nhat = set(Nhat_tmp)
        Nhat_tmp_name = Nhat_tmp
        # print(Nhat_tmp)
        all_components = set([])
        # print('counter')
        # print(counter)
        # print('pt1')
        # print(Nhat)
        if len(Nhat_tmp) >= 2:
            for first_inter in Nhat:
                for last_inter in Nhat-set([first_inter]):
                    tmp = Nhat-set([first_inter, last_inter])
                    tmp = sorted(list(tmp))
                    new_term = tuple([first_inter, last_inter, tuple(tmp)])
                    all_components.add(new_term)
        # print('pt2')

        if len(Nhat_tmp) == 1:

            new_term = tuple([list(Nhat)[0], list(Nhat)[0], tuple(set([]))])
            all_components.add(new_term)
            Nhat_tmp_name = new_term
        # print('pt3')

        if len(Nhat_tmp) == 0:
            new_term = tuple([None, None, tuple(set([]))])
            all_components.add(new_term)
            Nhat_tmp_name = new_term
            # input('checker2')
        # print('pt4')

        Nhat_tmp_name
        dict_inter_2_comp[Nhat_tmp_name] = all_components

        dict_all_inter_by_size[len(Nhat)].add(Nhat_tmp)

        for comp in all_components:

            dict_all_inter_pair_by_size[len(Nhat)].add(comp)
        # print('pt5')

    timeBef.append(timer()-start_time)
    print('step 4')
    start_time = timer()

    # print('dict_inter_2_comp')
    # print(dict_inter_2_comp)
    # print('dict_inter_2_comp')

    # let cost_2_pair be a mapping from
    pair_2_cost = dict()
    pair_2_ordering = dict()
    for i in range(0, 2):
        for my_inter_pair in dict_all_inter_pair_by_size[i]:
            print('my_inter_pair set zero')
            print(my_inter_pair)
            pair_2_cost[my_inter_pair] = 0
            if i == 0:
                pair_2_ordering[my_inter_pair] = None
            else:
                pair_2_ordering[my_inter_pair] = [my_inter_pair[0]]
    timeBef.append(timer()-start_time)
    print('step 5')
    start_time = timer()

    # print('TESTING')
    for num_inter in range(2, NumLA+1):
        print('here me here')
        print(num_inter)
        for my_inter_pair in dict_all_inter_pair_by_size[num_inter]:
            best_cost = np.inf
            best_pred = None
            w1 = my_inter_pair[0]
            w2 = my_inter_pair[1]
            Ninter = my_inter_pair[2]

            if len(set(Ninter)) == 0:
                added_cost = dist_mat[w1, w2]
                pair_2_cost[my_inter_pair] = added_cost
                pair_2_ordering[my_inter_pair] = [w1, w2]

            if len(set(Ninter)) == 1:
                k1 = list(Ninter)[0]
                added_cost = dist_mat[w1, k1]+dist_mat[k1, w2]
                pair_2_cost[my_inter_pair] = added_cost
                pair_2_ordering[my_inter_pair] = [w1, k1, w2]

            if len(set(Ninter)) >= 2:
                for poss_pred in dict_inter_2_comp[Ninter]:
                    k1 = poss_pred[0]
                    k2 = poss_pred[1]
                    candid_cost = pair_2_cost[poss_pred]
                    added_cost = dist_mat[w1, k1]+candid_cost+dist_mat[w2, k2]
                    if added_cost < best_cost:
                        # pred_ordering=pair_2_ordering[poss_pred]
                        # pair_2_cost[my_inter_pair]=added_cost
                        # pair_2_ordering[my_inter_pair]=[w1]+pred_ordering+[w2]
                        best_pred = poss_pred
                        best_cost = added_cost
                pred_ordering = pair_2_ordering[best_pred]
                pair_2_cost[my_inter_pair] = best_cost
                pair_2_ordering[my_inter_pair] = [w1]+pred_ordering+[w2]
    timeBef.append(timer()-start_time)
    print('step 6')
    start_time = timer()
    # input('yo')
    # print('pair_2_cost')
    # print(pair_2_cost)
    # print('pair_2_cost')
    dict_la_2_ordering = dict()
    dict_la_2_cost = dict()
    #
    All_LA = set([])
    for u in AllCust:
        my_la = tuple(['-1', u, tuple(set([]))])
        All_LA.add(my_la)

    for u in AllCust:
        poss_succ = set(AllCust)-set(LA_neigh[u])
        poss_succ = poss_succ-set([u])

        # print('poss_succBEFORE')
        # print(poss_succ)

        poss_succ.add('-2')
        #print('poss_succ AFTER')
        # print(poss_succ)
        for Nhat in all_inter_u[u]:  # powerset(LA_neigh[u]):
            tot_dem = 0
            tot_dem += tot_dem+demand[u]
            tot_dem += dictNhat2DemTot[tuple(Nhat)]
            for succ in poss_succ:
                if poss_succ != '-2' or tot_dem+demand[succ] <= capacity:
                    my_la = tuple([u, succ, tuple(Nhat)])

                    All_LA.add(my_la)
    timeBef.append(timer()-start_time)
    print('step 7')
    start_time = timer()

    dict_LA_2_cost = dict()
    dict_LA_2_ordering = dict()
    counter = 0
    big_len = len(All_LA)

    for my_la in All_LA:
        # print(counter/big_len)
        # print(my_la)
        u = my_la[0]
        v = my_la[1]
        Nhat = my_la[2]
        NhatSet = set(Nhat)
        if len(NhatSet) == 0:
            added_cost = 0
            if u != '-1' and v != '-2':
                added_cost = dist_mat[u, v]
            if u != '-1' and v == '-2':
                added_cost = dist_2_depot[u]
            if u == '-1' and v != '-2':
                added_cost = dist_2_depot[v]
            dict_LA_2_cost[my_la] = added_cost
            dict_LA_2_ordering[my_la] = [u, v]
        if len(NhatSet) == 1:
            k1 = list(NhatSet)[0]
            k2 = list(NhatSet)[0]
            added_cost = 0
            if u != '-1':
                added_cost = added_cost+dist_mat[u, k1]
            else:
                added_cost = added_cost+dist_2_depot[k1]
            if v != '-2':
                added_cost = added_cost+dist_mat[u, k2]
            else:
                added_cost = added_cost+dist_2_depot[k2]
            pred_ordering = [u, k1, v]
            dict_LA_2_cost[my_la] = added_cost
            dict_LA_2_ordering[my_la] = [u, k1, v]
        if len(NhatSet) > 2:
            # print('u')
            # print(u)
            # print('LA_neigh[u]')
            # print(LA_neigh[u])
            best_pred = None
            for poss_pred in dict_inter_2_comp[Nhat]:
                k1 = poss_pred[0]
                k2 = poss_pred[1]
                added_cost = 1*pair_2_cost[poss_pred]
                added_cost = added_cost+dist_mat[u, k1]
                added_cost = added_cost+dist_mat[u, k2]
                if added_cost < best_cost:

                    best_pred = poss_pred
                    best_cost = added_cost
            pred_ordering = pair_2_ordering[poss_pred]
            dict_LA_2_cost[my_la] = added_cost
            dict_LA_2_ordering[my_la] = [u]+pred_ordering+[v]
        counter = counter+1

    timeBef.append(timer()-start_time)
    print('done 8')
    print('timeBef')
    print(timeBef)
    print(sum(timeBef))

    return [dict_LA_2_ordering, dict_LA_2_cost]
