from tourrecomm import *
from operator import add
from functools import reduce

def poi2groupOP(algo, dfNodes, dfUserInt, groupUserList, startNode, endNode, budget, day, visitedNodePerUsr):

    results = pd.DataFrame(columns=['algo', 'startNode/endNode', 'budget', 'userID', 'totalPOI', 'totalCost', 'totalProfit', 'totalInterest' , 'reachEndNode', 'totalPopInt', 'maxInterest', 'minInterest', 'tour'])
    userIntByTime = pd.DataFrame(columns=dfUserInt.columns)

    for i in range(len(groupUserList)):
        userIntByTime = userIntByTime.append(dfUserInt.loc[dfUserInt['userID'] == groupUserList[i]])

    userIntByTime = userIntByTime.drop(['userID'], axis = 1)
    userIntByTime = userIntByTime.mean()
    userIntByTime = userIntByTime.reset_index()
    userIntByTime = userIntByTime.rename(columns={'index': 'category', 0: 'catIntLevel'})
    userIntByTime['userID'] = 'group'

    dfNodesPath = dfNodes.copy()
    dfNodesCal = dfNodes.copy()

    if algo == 'ranClusterOnce' or algo == 'CCKmeans' or algo == 'NormalKmeans':
        resultPath = clusterOnceOP(dfNodesPath, startNode, endNode, budget, day, userIntByTime)

        if len(resultPath.index) != 0:
            for tempUserID in groupUserList:
                tempDfUserInt = dfUserInt.loc[dfUserInt['userID'] == tempUserID]  # determine indv user interest
                #print(tempDfUserInt)
                userIntPerUser= pd.melt(tempDfUserInt, id_vars=['userID'], value_vars=['Cultural','Amusement','Shopping','Structure','Sport','Beach']) # determine indv user interest
                userIntPerUser = userIntPerUser.rename(columns={list(userIntPerUser)[0]:'userID', list(userIntPerUser)[1]:'category', list(userIntPerUser)[2]:'catIntLevel'})
                userInterest = userIntPerUser.copy()
                #print(userIntPerUser)
                #print(userInterest)
                stats = calcStats(resultPath, dfNodesCal, userInterest, endNode, day)
                results = results.append(pd.DataFrame([[algo,startNode,budget,tempUserID,stats.totalPOI.values[0],stats.totalDistance.values[0],stats.totalPopularity.values[0],stats.totalInterest.values[0],stats.completed.values[0],stats.totalPopInt.values[0],stats.maxInterest.values[0],stats.minInterest.values[0],stats.tour.values[0]]], columns = results.columns))
        else:
            for tempUserID in groupUserList:
                tempDfUserInt = dfUserInt.loc[dfUserInt['userID'] == tempUserID]  # determine indv user interest
                userIntPerUser= pd.melt(tempDfUserInt, id_vars=['userID'], value_vars=['Cultural','Amusement','Shopping','Structure','Sport','Beach']) # determine indv user interest
                userIntPerUser = userIntPerUser.rename(columns={list(userIntPerUser)[0]:'userID', list(userIntPerUser)[1]:'category', list(userIntPerUser)[2]:'catIntLevel'})
                results = results.append(pd.DataFrame([[algo,startNode,budget,tempUserID,np.nan,np.nan,np.nan,np.nan,np.nan,np.nan,np.nan,np.nan,np.nan]], columns = results.columns))
    elif algo == 'ClusterPerDayByInterest':
        temPath, visitedNodePerUsr = clusterPerDayOP(dfNodes, groupUserList, userIntByTime, startNode, endNode, budget, day, visitedNodePerUsr)
        print(visitedNodePerUsr)
        return temPath
    results = results.reset_index(drop=True)
    print(results)
    return results

# POI Recommendation to Tour Groups based on Orienteering Problem (random/kmeans clustering)
def clusterOnceOP(dfNodesPath, startNode, endNode, budget, day, userIntByTime):
    resultPath = pd.DataFrame()
    for loop in range(day):
        temPath = tourRecLPmultiObj(startNode, endNode, budget, dfNodesPath, None, userIntByTime, 0.5, False)
        visitedNode = []
        temPath['day'] = 'day ' + str(loop + 1)
        resultPath = resultPath.append(temPath)
        for index, row in temPath.iterrows():
            if row['from'] != startNode:
                visitedNode.append(row['from'])
        print('visitedNode: '+ str(visitedNode))
        for poi in visitedNode:
            dfNodesPath = dfNodesPath[dfNodesPath['from'] != poi]
        for poi in visitedNode:
            dfNodesPath = dfNodesPath[dfNodesPath['to'] != poi]
        dfNodesPath = dfNodesPath.reset_index(drop=True)
    resultPath = resultPath.reset_index(drop=True)
    return resultPath

# POI Recommendation to Tour Groups based on Orienteering Problem (random clustering everyday)
def clusterPerDayOP(dfNodesPath, groupUserList, userIntByTime, startNode, endNode, budget, day, visitedNodePerUsr):

    visitedNode = []
    for user in groupUserList:
        if user in visitedNodePerUsr.keys():
            #print(user)
            visitedNode.append(visitedNodePerUsr[user])
    if len(visitedNode) != 0:
        visitedNode = reduce(add, visitedNode)
        visitedNode = list(dict.fromkeys(visitedNode))
    #print(visitedNode)
    for poi in visitedNode:
        if poi != startNode:
            dfNodesPath = dfNodesPath[dfNodesPath['from'] != poi]
    for poi in visitedNode:
        if poi != startNode:
            dfNodesPath = dfNodesPath[dfNodesPath['to'] != poi]
    dfNodesPath = dfNodesPath.reset_index(drop=True)
    print(dfNodesPath)
    ranTemPath = tourRecLPmultiObj(startNode, endNode, budget, dfNodesPath, None, userIntByTime, 0.5, False)
    #print('rantempath')
    #print(ranTemPath.to_string)
    ranTemPath['day'] = 'day ' + str(day + 1)
    # store user's visited nodes
    for user in groupUserList:
        if ranTemPath.empty is False:
            for poi in ranTemPath.to:
                #if poi != startNode:
                    visitedNodePerUsr.setdefault(user, [])
                    visitedNodePerUsr[user].append(poi)

    #print(visitedNodePerUsr)
    #print(len(visitedNodePerUsr))
    return ranTemPath, visitedNodePerUsr


# calculate the statistic for each user in random and kmeans clustering
def calcStats(solnRecTour, dfNodesCal, userInterest, endNode, day):

    dfNodes = dfNodesCal.copy()
    # normalize the popularity and interest to [0,1]
    dfNodes.profit = dfNodes.profit / max(dfNodes.profit)
    userInterest.catIntLevel = userInterest.catIntLevel / max(userInterest.catIntLevel)
    #print(userInterest)

    # calculate the total popularity and interest for the entire tour
    totalPOI = len(solnRecTour.index) - day
    totalDistance = 0
    totalPopularity = 0
    totalInterest = 0
    totalPopInt = 0
    interestLevels = []
    tour = []
    for i in range(len(solnRecTour.index)):
        tempFrom = solnRecTour.iloc[i]['from']
        tempTo = solnRecTour.iloc[i]['to']
        tempCost = dfNodes.loc[(dfNodes['from'] == tempFrom) & (dfNodes['to'] == tempTo), 'cost'].values[0]

        tempProfit = dfNodes.loc[(dfNodes['from'] == tempFrom) & (dfNodes['to'] == tempTo), 'profit'].values[0]

        tempCategory = dfNodes.loc[(dfNodes['from'] == tempFrom) & (dfNodes['to'] == tempTo), 'category'].values[0]

        totalDistance = totalDistance + tempCost
        totalPopularity = totalPopularity + tempProfit
        if tempCategory in list(userInterest['category']):
            totalInterest = totalInterest + userInterest.loc[userInterest['category'] == tempCategory, "catIntLevel"].values[0]
            #print('userInterest: '+ str(totalInterest))
            interestLevels.append(userInterest.loc[userInterest['category'] == tempCategory, "catIntLevel"].values[0])
        tour.append(tempFrom)
    tour.append(solnRecTour.iloc[len(solnRecTour.index) -1]['to'])
    tour = '-'.join(str(poi) for poi in tour)
    totalPopInt = 0.5 * totalPopularity + 0.5 * totalInterest
    completed = (solnRecTour.iloc[len(solnRecTour.index)-1]['to'] == endNode) & (len(solnRecTour.index) != 0)
    stats = pd.DataFrame([[totalPOI, totalDistance, totalPopularity, totalInterest, completed, totalPopInt, max(interestLevels), min(interestLevels), tour]], columns=['totalPOI', 'totalDistance', 'totalPopularity', 'totalInterest', 'completed', 'totalPopInt', 'maxInterest', 'minInterest', 'tour'])
    #print(stats)
    return stats

# calculate the statistics for groups that users are clustered everyday
def calcStatsRan(visitedNodePerUsr, dfNodes, dfUserInt, startNode, budget, day):


    results = pd.DataFrame(columns=['algo', 'startNode/endNode', 'budget', 'userID', 'totalPOI', 'totalCost', 'totalProfit',
                 'totalInterest', 'reachEndNode', 'totalPopInt', 'maxInterest', 'minInterest', 'tour'])

    for user in visitedNodePerUsr.keys():
        tempDfUserInt = dfUserInt.loc[dfUserInt['userID'] == user]
        userIntPerUser = pd.melt(tempDfUserInt, id_vars=['userID'], value_vars=['Cultural', 'Amusement', 'Shopping', 'Structure', 'Sport', 'Beach'])  # determine indv user interest
        userIntPerUser = userIntPerUser.rename(columns={list(userIntPerUser)[0]: 'userID', list(userIntPerUser)[1]: 'category', list(userIntPerUser)[2]: 'catIntLevel'})
        userInterest = userIntPerUser.copy()
        dfNodesCal = dfNodes.copy()

        dfNodesCal.profit = dfNodesCal.profit / max(dfNodesCal.profit)
        userInterest.catIntLevel = userInterest.catIntLevel / max(userInterest.catIntLevel)

        totalDistance = 0
        totalPopularity = 0
        totalInterest = 0
        totalPopInt = 0
        interestLevels = []
        indvUsrPath = visitedNodePerUsr[user]
        totalPOI = len(indvUsrPath) - indvUsrPath.count(startNode)
        #print(indvUsrPath)
        for i in range(len(indvUsrPath) - 1):
            tempFrom = indvUsrPath[i]
            tempTo = indvUsrPath[i + 1]
            tempCost = dfNodesCal.loc[(dfNodesCal['from'] == tempFrom) & (dfNodesCal['to'] == tempTo), 'cost'].values[0]

            tempProfit = dfNodesCal.loc[(dfNodesCal['from'] == tempFrom) & (dfNodesCal['to'] == tempTo), 'profit'].values[0]

            tempCategory = dfNodesCal.loc[(dfNodesCal['from'] == tempFrom) & (dfNodesCal['to'] == tempTo), 'category'].values[0]
            #print('totalcost: ' + str(tempCost))
            totalDistance = totalDistance + tempCost
            totalPopularity = totalPopularity + tempProfit
            if tempCategory in list(userInterest['category']):
                totalInterest = totalInterest + userInterest.loc[userInterest['category'] == tempCategory, "catIntLevel"].values[0]
                interestLevels.append(userInterest.loc[userInterest['category'] == tempCategory, "catIntLevel"].values[0])
                #print(interestLevels)
            totalPopInt = 0.5 * totalPopularity + 0.5 * totalInterest
            completed = (indvUsrPath[-1] == startNode) & (indvUsrPath.count(startNode) == (day + 1))
        tour = '-'.join(str(poi) for poi in indvUsrPath)
        stats = pd.DataFrame([[totalPOI, totalDistance, totalPopularity, totalInterest, completed, totalPopInt, max(interestLevels), min(interestLevels), tour]], columns=['totalPOI', 'totalDistance', 'totalPopularity', 'totalInterest', 'completed', 'totalPopInt', 'maxInterest', 'minInterest', 'tour'])
        results = results.append(pd.DataFrame([['ClusterPerDayByInterest', startNode, budget, user, stats.totalPOI.values[0],
                                      stats.totalDistance.values[0], stats.totalPopularity.values[0],
                                      stats.totalInterest.values[0], stats.completed.values[0],
                                      stats.totalPopInt.values[0], stats.maxInterest.values[0],
                                      stats.minInterest.values[0], stats.tour.values[0]]], columns=results.columns))

    results = results.reset_index(drop=True)
    print(results)
    return results