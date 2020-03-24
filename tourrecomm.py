import pandas as pd
import numpy as np
from pulp import *
from scipy.optimize import linprog


# core linear programming function
def tourRecLPmultiObj(startNode, endNode, budget, dfNodesTour, subtourCons, userInterest, intWeight, normInterest):
    dfNodes = dfNodesTour.copy()
    results = tourrecommendationloop(startNode, endNode, budget, dfNodes, subtourCons, userInterest, intWeight,
                                     normInterest)

    while len(results.columns) == len(dfNodes.index):
        subtourCons = results
        results = tourrecommendationloop(startNode, endNode, budget, dfNodes, subtourCons, userInterest, intWeight,
                                         normInterest)
        if len(results.columns) == len(dfNodes.index):
            subtourCons = results

    return (results)


def tourrecommendationloop(startNode, endNode, budget, dfNodes, subtourCons, userInterest, intWeight, normInterest):
    # get the links that connect either the start and/or end nodes
    startNodeList = list(dfNodes[dfNodes['from'] == startNode].index)
    endNodeList = list(dfNodes[dfNodes['to'] == endNode].index)

    # for the constraint "no node re-visits"
    # matrix to indicate which links belong to the same node
    ind = 0
    nodeRevisit = pd.DataFrame(
        np.zeros(shape=(len(dfNodes['from'].unique()) + len(dfNodes['to'].unique()), len(dfNodes.index)), dtype=int))
    for tempNode in dfNodes['from'].unique():
        nodeRevisit.iloc[ind, list(dfNodes[dfNodes['from'] == tempNode].index)] = 1
        ind = ind + 1
    for tempNode in dfNodes['to'].unique():
        nodeRevisit.iloc[ind, list(dfNodes[dfNodes['to'] == tempNode].index)] = 1
        ind = ind + 1

    # for the constraint "connectivity of paths" (nodes with an in-link must have an out-link, unless its the start/end node)
    # matrix to indicate which nodes shd be connected (dfNodes$from and dfNodes$to shd be the same size since its a matrix)
    nodeConnect = pd.DataFrame(np.zeros(shape=(len(dfNodes['from'].unique()), len(dfNodes.index)), dtype=int))
    ind = 0
    for tempNode in dfNodes['from'].unique():
        # if (tempNode != startNode) & (tempNode != endNode):
        # nodeConnect.iloc[ind, list(dfNodes[(dfNodes['to'] == tempNode) & (dfNodes['from'] != endNode)].index)] = 1  # the in-links
        nodeConnect.iloc[ind, list(dfNodes[(dfNodes['to'] == tempNode)].index)] = 1
        # nodeConnect.iloc[ind, list(dfNodes[(dfNodes['from'] == tempNode) & (dfNodes['to'] != startNode)].index)] = -1  # the out-links
        nodeConnect.iloc[ind, list(dfNodes[(dfNodes['from'] == tempNode)].index)] = -1
        ind = ind + 1
    '''
    # for the constraint "no start-end paths" (i.e., no direct startNode-endNode path, if not results are not meaningful)
    nodeStartEnd = pd.DataFrame(np.zeros(shape = (1, len(dfNodes.index)), dtype = int))
    nodeStartEnd.iloc[0, list(dfNodes[(dfNodes['from'] == startNode) & (dfNodes['to'] == endNode)].index)] = 1
    '''
    '''
    # for the constraint "uni-links to start/end nodes" (i.e., start node only has out-links, end node only has in-links)
    nodeUniLink = pd.DataFrame(np.zeros(shape = (2,len(dfNodes.index)), dtype = int))
    nodeUniLink.iloc[0, list(dfNodes[dfNodes['to'] == startNode].index)] = 1  # start node only has out-links
    nodeUniLink.iloc[1, list(dfNodes[dfNodes['from'] == endNode].index)] = 1  # end node only has in-links
    '''

    # for the constraint "no sub-tours"
    if subtourCons is None:
        subtourCons = pd.DataFrame(np.zeros(shape=(1, len(dfNodes.index)), dtype=int))
    noSubtours = subtourCons.reset_index(drop=True)
    print(noSubtours.to_string())

    # for the constraint "no exceed budget"
    nodeBudget = pd.DataFrame(np.zeros(shape=(1, len(dfNodes.index))))
    ind = 0
    for tempCost in dfNodes['cost']:
        nodeBudget.iloc[0, ind] = tempCost
        ind = ind + 1

    # for the constraint fix start and end node
    startNodeCons = pd.DataFrame(np.zeros(shape=(1, len(dfNodes.index)), dtype=int))
    endNodeCons = pd.DataFrame(np.zeros(shape=(1, len(dfNodes.index)), dtype=int))
    for tempNode in startNodeList:
        startNodeCons.iloc[0, tempNode] = 1
    for tempNode in endNodeList:
        endNodeCons.iloc[0, tempNode] = 1

    # set objective function to optimize
    dfNodes.profit = dfNodes.profit / max(dfNodes.profit)  # normalize the popularity to [0,1]
    if normInterest == True:  # whether to normalize user interest or use the raw values
        userInterest.catIntLevel = userInterest.catIntLevel / max(
            userInterest.catIntLevel)  # normalize user interests to [0,1]

    for i in range(
            len(dfNodes.index)):  # combine POI Popularity and User Interest into a single multi-objective function
        intLevel = 0  # default interest level = 0, if the user has never visited POI of this category
        if any(userInterest.category == dfNodes.iloc[i, :]['category']) & (dfNodes.iloc[i]['to'] != startNode):
            intLevel = \
            userInterest.loc[userInterest.category == dfNodes.iloc[i, :]['category']][['catIntLevel']].values[0]
            tempValue = dfNodes.iloc[i]["profit"]
            dfNodes.at[i, 'profit'] = (
                                                  1 - intWeight) * tempValue + intWeight * intLevel  # the combined multi-objective function

    # create an LP model
    # set up decision variable for each  poi X to poi Y
    visiting_status = pulp.LpVariable.dicts("visiting_status", (is_visit for is_visit in dfNodes.index), cat='Binary')
    # set objective function to maximize the profit
    model = pulp.LpProblem("GroupRecommendation", pulp.LpMaximize)
    model += pulp.lpSum(visiting_status[is_visit] * dfNodes.iloc[is_visit]['profit'] for is_visit in dfNodes.index)

    # build our constraints
    # constraint cost <= budget
    model += pulp.lpSum(
        visiting_status[is_visit] * nodeBudget.iloc[0][is_visit] for is_visit in dfNodes.index) <= budget

    # constraint start from a certain node
    model += pulp.lpSum(visiting_status[is_visit] * startNodeCons.iloc[0][is_visit] for is_visit in dfNodes.index) == 1

    # constraint end from a certain node
    model += pulp.lpSum(visiting_status[is_visit] * endNodeCons.iloc[0][is_visit] for is_visit in dfNodes.index) == 1

    # constraint no revisit node
    for i in nodeRevisit.index:
        model += pulp.lpSum(
            visiting_status[is_visit] * nodeRevisit.iloc[i][is_visit] for is_visit in dfNodes.index) <= 1

    # constraint path is connective
    for i in nodeConnect.index:
        model += pulp.lpSum(
            visiting_status[is_visit] * nodeConnect.iloc[i][is_visit] for is_visit in dfNodes.index) == 0

    '''
    # constraint no start-end path
    #model += pulp.lpSum(visiting_status[is_visit] * nodeStartEnd.iloc[0][is_visit] for is_visit in dfNodes.index) == 0


    # constraint  start only has out link & end only has in link
    #for i in nodeUniLink.index:
        #model += pulp.lpSum(visiting_status[is_visit] * nodeUniLink.iloc[i][is_visit] for is_visit in dfNodes.index) == 0
    '''

    # constraint "no sub-tours"
    ind = -1
    for i in noSubtours.index:
        ind = ind + 1
        # break subtours by setting constraint of RHS having <= subtourEdgeCount-1
        rhsValue = noSubtours.sum(axis=1, skipna=True)[ind] - 1
        # print(rhsValue)
        if (rhsValue < 0):
            rhsValue = 0
        model += pulp.lpSum(
            visiting_status[is_visit] * noSubtours.iloc[i][is_visit] for is_visit in dfNodes.index) <= rhsValue

    # solve LP
    model.solve()
    # print(model)
    for i in dfNodes.index:
        if visiting_status[i].varValue == 1:
            print(f"visiting_status {i}: {visiting_status[i].varValue}")
    dfTemp = pd.DataFrame(columns=dfNodes.columns)
    dfSoln = dfTemp = pd.DataFrame(columns=dfNodes.columns)
    if pulp.LpStatus[model.status] == 'Optimal':
        for i in dfNodes.index:
            if visiting_status[i].varValue == 1:
                dfTemp = dfTemp.append(dfNodes.iloc[[i]])
        print(dfTemp)
        tempNode = startNode
        newSubtourCons = pd.DataFrame(np.zeros(shape=(int(len(dfTemp.index) / 2), len(dfNodes.index)), dtype=int))

        ind = 0

        # store ordered path (start - end) to dfSoln
        while True:
            dfSoln = dfSoln.append(dfTemp[dfTemp['from'] == tempNode])
            prevTempNode = tempNode
            tempNode = dfTemp[dfTemp['from'] == tempNode].iloc[0]['to']
            dfTemp = dfTemp[dfTemp['from'] != prevTempNode]  # any leftovers will be subtours
            newSubtourCons.iloc[ind, list(dfNodes[(dfNodes['from'] == prevTempNode) & (
                        dfNodes['to'] == tempNode)].index)] = 1  # new subtour constraint
            if tempNode == endNode:
                break
        print(dfTemp)
        print(dfSoln)

        # check for subtours
        if len(dfTemp.index) != 0:
            while len(dfTemp.index) != 0:
                ind = ind + 1
                subtourNode = dfTemp.iloc[0]['from']  # a subtour has the same start and end node
                tempNode = dfTemp.iloc[0]['to']

                newSubtourCons.iloc[
                    ind, list(dfNodes[(dfNodes['from'] == subtourNode) & (dfNodes['to'] == tempNode)].index)] = 1
                dfTemp = dfTemp[dfTemp['from'] != subtourNode]  # any leftovers will be additional subtours

                while tempNode != subtourNode:
                    prevTempNode = tempNode
                    tempNode = dfTemp[dfTemp['from'] == tempNode].iloc[0]['to']
                    newSubtourCons.iloc[ind, list(dfNodes[(dfNodes['from'] == prevTempNode) & (
                                dfNodes['to'] == tempNode)].index)] = 1  # new subtour constraint
                    dfTemp = dfTemp[dfTemp['from'] != prevTempNode]  # any leftovers will be additional subtours

            newSubtourCons = newSubtourCons[0:ind + 1]
            subtourCons = subtourCons.append(newSubtourCons)  # add these new subtour constraints to any earlier ones
            return (subtourCons)  # return the new constraints, if solution is not found

    # dfSoln['profit'] = pulp.value(model.objective)
    return (dfSoln)


