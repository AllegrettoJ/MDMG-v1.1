#!/usr/bin/env python
# -*- coding: utf-8 -*-

#from __future__ import print_function
from cop_kmeans import cop_kmeans, l2_distance
from groupList import *
import argparse


def read_data(datafile):
    data = []
    with open(datafile, 'r') as f:
        for line in f:
            line = line.strip()
            if line != '':
                d = [float(i) for i in line.split()]
                data.append(d)

    return data

def read_constraints(consfile):
    ml, cl = [], []
    with open(consfile, 'r') as f:
        for line in f:
            line = line.strip()
            if line != '':
                line = line.split()
                constraint = (int(line[0]), int(line[1]))
                c = int(line[2])
                if c == 1:
                    ml.append(constraint)
                if c == -1:
                    cl.append(constraint)
    print(ml)
    print(cl)
    dfMustLink = pd.DataFrame(ml, columns=['userID1', 'userID2'])
    print(dfMustLink)
    dfMustLink.to_csv('mustLink.csv', index=False, sep=';', encoding='utf-8')
    return ml, cl

def run(datafile, consfile, k, n_rep, max_iter, tolerance):
    data = read_data(datafile)
    ml, cl = read_constraints(consfile)

    best_clusters = None
    best_score = None
    for _ in range(n_rep):
        clusters, centers = cop_kmeans(data, k, ml, cl,
                                       max_iter=max_iter,
                                       tol=tolerance)
        if clusters is not None and centers is not None:
            score = sum(l2_distance(data[j], centers[clusters[j]])
                        for j in range(len(data)))
            if best_score is None or score < best_score:
                best_score = score
                best_clusters = clusters
    return best_clusters


