import random
import math
import time
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
from calcinterest import *
from poi2group import *
from calcStat import *
from run_ckm import *
from groupList import *

# read userid from a csvfile
dfIntOriginal = pd.read_csv('userInt-URelTime-Toro.csv', sep=";")
dfNodes = pd.read_csv("costProfCat-ToroPOI-all.csv", sep=";")
dfVisits = pd.read_csv("userVisits-Toro-allPOI.csv", sep=";")

'''
dfNodes = pd.read_csv("costProfCat-BudaPOI-all.csv", sep=";")
dfVisits = pd.read_csv("userVisits-Buda-allPOI.csv", sep=";")
dfNodes = dfNodes.replace({'category': {'Park': 'Amusement', 'Historical': 'Structure', 'Museum': 'Beach', 'Transport': 'Sport'}})
dfVisits = dfVisits.replace({'poiTheme': {'Park': 'Amusementt', 'Historical': 'Structure', 'Museum': 'Beach', 'Transport': 'Sport'}})
print(dfVisits)
print(dfNodes)
'''

dfVisitTimes, dfavgDuration = addVisitDuration(dfVisits)
dfVisitTimes.visitDuration = dfVisitTimes.visitDuration / 60
dfVisitTimes.avgDuration = dfVisitTimes.avgDuration / 60

# only include nodes where we can determine a visitDuration
poiIncludeList = dfVisitTimes['poiID'].unique()
dfNodes['fromisin'] = dfNodes['from'].isin(poiIncludeList)
dfNodes = dfNodes[dfNodes.fromisin]
dfNodes = dfNodes.drop(['fromisin'], axis=1)

dfNodes['toisin'] = dfNodes['to'].isin(poiIncludeList)
dfNodes = dfNodes[dfNodes.toisin]
dfNodes = dfNodes.drop(['toisin'], axis=1)

dfNodes.cost = dfNodes.cost * 0.012

dfNodes = dfNodes.reset_index(drop=True)

dfNodesOrignal = dfNodes.copy()
# print(dfNodes.to_string())
# dfNodesAvg['visitDuration'] = np.nan

# construct the [dfNodesAvg] from [dfNodes] where "cost" = "walking time" + "avg. POI visit duration"
for poi in range(len(dfavgDuration)):
    dfNodesOrignal.loc[dfNodesOrignal['to'] == dfavgDuration.poiID[poi], 'cost'] = dfavgDuration.avgDuration[
                                                                                       poi] / 60 + dfNodesOrignal.cost
    # dfNodesAvg.loc[dfNodesAvg['to'] == dfavgDuration.poiID[poi], 'avgDuration'] = dfavgDuration.avgDuration[poi]/60

# pre-processing
dfVisits = dfVisits.drop_duplicates(subset=['seqID', 'poiID'])
seqCount = dfVisits.groupby(["seqID"]).size().reset_index(name='seqFreq')
dfVisits = dfVisits.merge(seqCount, left_on='seqID', right_on='seqID')
dfVisits = dfVisits.sort_values(['seqID', 'dateTaken'], ascending=True)
dfVisitsAll = dfVisits
dfVisits = dfVisits[dfVisits.seqFreq >= 3]

userID = []
userID_Int = []
num_of_user_to_select = 150  # set the number to select here
groupCount = 5
totalLoops = len(dfVisits.seqID.unique())

# data frame to hold overall results for the poi2group recommendation
resultsMean = pd.DataFrame()
resultsPOI2Group = pd.DataFrame()

print('totalLoops: ' + str(totalLoops))

'''
# data frame to hold overall results in the form 
# "algoName", "iteration count", "groupSize", "interest cosine similarity (continuous)", 
# "interest cosine similarity (binary)", "ratio of common top interest"
'''
results = pd.DataFrame(columns=['algo', 'iter', 'groupSize', 'intCosSim', 'intCosSimBin', 'topintRatio', 'intJaccard'])

budgetList = []
for loopNo in range(totalLoops):
    dfNodesAvg = dfNodesOrignal.copy()
    tempSeqID = dfVisits.seqID.unique()[loopNo]
    tempDfVisits = dfVisits[dfVisits.seqID == tempSeqID]  # get subset of [dfVisits] of this visit sequence [tempSeqID]
    startNode = tempDfVisits['poiID'].iloc[
        0]  # since [dfVisits] is ordered by userID and time, the startNode is the first entry
    budget = 0
    for i in range(len(tempDfVisits) - 1):
        budget = budget + dfNodesAvg.loc[(dfNodesAvg['from'] == tempDfVisits['poiID'].iloc[i]) & (
                dfNodesAvg['to'] == tempDfVisits['poiID'].iloc[i + 1]), 'cost'].values[0]
    budgetList.append(budget)
print(budgetList)

# draw the edf of time budget
x = budgetList
x = np.sort(x)
y = np.arange(1, len(x) + 1) / (len(x))
per95 = np.percentile(x, 95)
print('95 percentile: '+ str(per95) + 'mins')
plt.plot(x, y, marker='.')
plt.title('Emperical distribution function')
plt.xlabel('Time Budget (minutes)')
plt.ylabel('Fraction of Data')
plt.axvline(x=per95, color='k', linestyle=':', label='95 percentile')
plt.legend(loc='lower right')
plt.xticks(np.arange(0, 1300, 100))
# plt.savefig('ECDF total sample.png')

# iteratively test the various user2group and poi2group algorithms for X no. of times
for loopNo in range(5):
    resultPOI2GroupRan = pd.DataFrame()
    resultsPOI2GroupRanByDay = pd.DataFrame()
    resultsPOI2GroupKmean = pd.DataFrame()

    resultsPOI2GroupNormalKmean = pd.DataFrame()

    print('loopNo: ' + str(loopNo + 1))
    dfNodesAvg = dfNodesOrignal.copy()
    dfInterests = dfIntOriginal.copy()
    # print(dfInterests)
    # print(dfNodesAvg)
    dfInterests = dfInterests.sample(num_of_user_to_select)  # randomly select [totalUsers] users from the whole list

    # select the start/end POI and budget based on this current real-life travel sequence
    tempSeqID = dfVisits.seqID.unique()[loopNo]
    tempDfVisits = dfVisits[dfVisits.seqID == tempSeqID]  # get subset of [dfVisits] of this visit sequence [tempSeqID]
    startNode = tempDfVisits['poiID'].iloc[
        0]  # since [dfVisits] is ordered by userID and time, the startNode is the first entry
    endNode = startNode

    # startNode = 21
    # endNode = 21

    # set up endNode profit and visiting time to 0
    startNodeVT = dfavgDuration.loc[dfavgDuration.poiID == startNode].iloc[0][
                      'avgDuration'] / 60  # calculate endNode visiting time
    dfNodesAvg.loc[dfNodesAvg['to'] == startNode, 'cost'] -= startNodeVT
    dfNodesAvg.loc[dfNodesAvg['to'] == startNode, 'profit'] = 0
    # endNode = tempDfVisits['poiID'].iloc[len(tempDfVisits) - 1] # similarly, endNode is the last entry

    # budget will be the actual distance covered between the POIs in the [tempDfVisits]
    # budget  = random.randrange(5,9,1) * 60 #  budget is randomly selected from 5hr to 8hr
    budget = 0
    for i in range(len(tempDfVisits) - 1):
        budget = budget + dfNodesAvg.loc[(dfNodesAvg['from'] == tempDfVisits['poiID'].iloc[i]) & (
                    dfNodesAvg['to'] == tempDfVisits['poiID'].iloc[i + 1]), 'cost'].values[0]
    # the daily visiting time should not over 8hrs (480min)
    # if budget > 480:
    #    budget = 480
    #budget = 200

    # set the visiting day
    day = 3
    visitedNodePerUsr = {}
    print('budget:' + str(budget))
    print('startNode:' + str(startNode))
    print('travelDay: ' + str(day))

    # record start time
    rantime = time.time()


    # random clustering (cluster only once)
    randUserIDs = list(dfInterests['userID'])
    random.shuffle(randUserIDs)
    groupSize = int(math.floor(len(randUserIDs)/groupCount)) # get the approx size of each group

    currentID = 0


    dfInterests = pd.read_csv('dfInterests150Ori.csv', sep=";")
    #print(dfInterests.to_string())
    randUserIDs = list(dfInterests['userID'])
    #print(randUserIDs)
    random.shuffle(randUserIDs)
    groupSize = int(math.floor(len(randUserIDs) / groupCount))  # get the approx size of each group



    for i in range(groupCount):
        if i != groupCount:
            nextID = currentID + groupSize
        else:
            nextID = len(randUserIDs)

    #nextID = currentID + groupSize
        groupUserList = randUserIDs[currentID:nextID] # userIDs of all users in this group

        # perform the user2group assignment and record the results
        results = results.append(pd.DataFrame([['ranClusterOnce', loopNo + 1, len(groupUserList), calcIntCosSim(groupUserList, dfInterests, True), calcIntCosSim(groupUserList, dfInterests, False), calcTopIntRatio(groupUserList, dfInterests), calcIntJaccard(groupUserList, dfInterests)]], columns = results.columns))
        print(results)
        currentID = nextID

        # perform the poi2group recommendation and record the results
        tempResults = poi2groupOP('ranClusterOnce', dfNodesAvg, dfInterests, groupUserList, startNode, endNode, budget, day, visitedNodePerUsr)
        # tempResults['cluster'] = 'random'
        tempResults['iter'] = loopNo + 1
        tempResults['groupID'] = i + 1
        resultPOI2GroupRan = resultPOI2GroupRan.append(tempResults)

    # calculate the running time for random clustering
    rantime = time.time() - rantime


    # record start time
    # ranPerDaytime = time.time()
    # random clustering (each day cluster the users)
    dfNodesRandom = dfNodesAvg.copy()
    temVisitingPath = {}
    randUserIDs = list(dfInterests['userID'])
    groupSize = int(math.floor(len(randUserIDs) / groupCount))  # get the approx size of each group

    dfInterests = pd.read_csv('dfInterests150Ori.csv', sep=";")
    print(dfInterests)
    groupchanged = False
    dfInt = dfInterests.copy()

    for travelDay in range(day):
        print('day ' + str(travelDay))

        currentID = 0

        if groupchanged == True:
            print(dfNodesRandom)
            dfIntUpdate = dfInt.copy()
            print('------------------------------------------------')
            print(visitedNodePerUsr)
            print('------------------------------------------------')

            for user in dfInt['userID']:
                for key, value in visitedNodePerUsr.items():
                    if user == key:
                        print(key)
                        print(value)
                        print(dfIntUpdate.loc[dfIntUpdate['userID'] == user])
                        for node in value:
                            print('#################')
                            print(node)
                            cat = dfNodes[dfNodes['to'] == node]['category'].values[0]
                            dfIntUpdate.loc[(dfIntUpdate.userID == user), cat] = dfIntUpdate.loc[(
                                                                                                             dfIntUpdate.userID == user), cat] * (
                                                                                             1 - 0.1)
                            print(dfIntUpdate.loc[dfIntUpdate['userID'] == user])
                            print(cat)
                            print('-----------------')

                        break
            print(dfIntUpdate)
            print(dfInterests)



        # nextID = currentID + groupSize

        # dfInt = dfInterests.drop(['userID'], axis=1)

        if groupchanged == True:
            dfInt = dfIntUpdate.copy()
        print(dfInt)

        #category = list(dfInt.columns)
        #print(category)

        userIDList = dfInt['userID']
        dfIntExUserID = dfInt.drop(['userID'], axis=1)
        # dfInterests_exUserID = dfInterests.drop(['userID'], axis=1)

        print(dfInt.to_string())

        dfIntExUserID.to_csv('dfInterests_exUserID.csv', header=None, index=False, sep='\t', encoding='utf-8')
        userIDList.to_csv('userID.csv', header=None, index=False, sep='\t', encoding='utf-8')

        print(userIDList)
        # dfInterests100 = pd.read_csv('dfInterests100.csv', sep='\t')

        clusters = run('dfInterests_exUserID.csv', 'link.constraints', 5, 10, 300, 1e-4)
        print(clusters)
        groupUserListProcess(clusters)

        currentID = 0
        groupchanged = True
        print(dfInt)

        '''
        kmeans = KMeans(n_clusters=groupCount, random_state=0).fit(
            dfInt[['Cultural', 'Amusement', 'Shopping', 'Structure', 'Sport', 'Beach']])
        dfInt['groupID'] = kmeans.labels_
        dfInt = dfInt.sort_values(['groupID'], ascending=True)
        '''

        for i in range(groupCount):
            groupUserList = []

           

            with open('file.csv', 'r') as f:
                sentence_list = [[s.strip()] for s in f]
                groupUserList = [v.rstrip().split(",") for v in sentence_list[i]]
                groupUserList = [j for sub in groupUserList for j in sub]
                print(groupUserList)

            # dfInterests = pd.read_csv('dfInterests150Ori.csv', sep=";")

            '''
            for j in range(len(dfInt.index)):
                if dfInt.iloc[j]['groupID'] == i:
                    groupUserList.append(dfInt.iloc[j]['userID'])
            '''

            print(groupUserList)

            if travelDay == 0:
                if i == 0:
                    setA = set(groupUserList)
                    Day1 = {'setA': setA}
                elif i == 1:
                    setB = set(groupUserList)
                    Day1['setB'] = setB
                elif i == 2:
                    setC = set(groupUserList)
                    Day1['setC'] = setC
                elif i == 3:
                    setD = set(groupUserList)
                    Day1['setD'] = setD
                else:
                    setE = set(groupUserList)
                    Day1['setE'] = setE
            elif travelDay == 1:
                if i == 0:
                    setA = set(groupUserList)
                    Day2 = {'setA': setA}
                elif i == 1:
                    setB = set(groupUserList)
                    Day2['setB'] = setB
                elif i == 2:
                    setC = set(groupUserList)
                    Day2['setC'] = setC
                elif i == 3:
                    setD = set(groupUserList)
                    Day2['setD'] = setD
                else:
                    setE = set(groupUserList)
                    Day2['setE'] = setE

            print('------------Day 1------------')
            print(dfInterests)
            print(groupUserList)

            # groupUserList = randUserIDs[currentID:nextID]  # userIDs of all users in this group
            results = results.append(pd.DataFrame([['ClusterPerDayByInterest', loopNo + 1, len(groupUserList),
                                                    calcIntCosSim(groupUserList, dfInterests, True),
                                                    calcIntCosSim(groupUserList, dfInterests, False),
                                                    calcTopIntRatio(groupUserList, dfInterests),
                                                    calcIntJaccard(groupUserList, dfInterests)]],
                                                  columns=results.columns))
            print(results)

            # currentID = nextID
            temVisitingPath['group' + str(i + 1)] = groupUserList
            tempResults = poi2groupOP('ClusterPerDayByInterest', dfNodesRandom, dfInterests,
                                      temVisitingPath['group' + str(i + 1)], startNode, endNode,
                                      budget, travelDay, visitedNodePerUsr)
            tempResults['groupID'] = (i + 1) * (travelDay + 1)
            resultsPOI2GroupRanByDay = resultsPOI2GroupRanByDay.append(tempResults)
            resultsPOI2GroupRanByDay = resultsPOI2GroupRanByDay.reset_index(drop=True)
            resultsPOI2GroupRanByDay = resultsPOI2GroupRanByDay.sort_values(['groupID', 'day'], ascending=True)

        # f = open("dict.txt", "w")
        # f.write(str(visitedNodePerUsr))
        # f.close()
        # print('------------------------------------------------')
        # print(resultsPOI2GroupRanByDay)
        # print(visitedNodePerUsr)
        # print('------------------------------------------------')

    for user in visitedNodePerUsr.keys():
        visitedNodePerUsr[user].insert(0, startNode)

    resultsPOI2GroupRanByDay = calcStatsRan(visitedNodePerUsr, dfNodesAvg, dfInterests, startNode, budget, day)
    # resultsPOI2GroupRanByDay['cluster'] = 'randomByDay'
    resultsPOI2GroupRanByDay['iter'] = loopNo + 1
    resultsPOI2GroupRanByDay['groupID'] = np.nan
    # calculate running time for randomByDay clustering
    # ranPerDaytime = time.time() - ranPerDaytime


    print(resultsPOI2GroupRanByDay)




    # kmeans clustering
    dfInt = dfInterests.drop(['userID'], axis=1)
    dfInt = dfInterests.copy()

    kmeans = KMeans(n_clusters=groupCount, random_state=0).fit(
        dfInt[['Cultural', 'Amusement', 'Shopping', 'Structure', 'Sport', 'Beach']])
    dfInt['groupID'] = kmeans.labels_
    dfInt = dfInt.sort_values(['groupID'], ascending=True)
    currentID = 0

    for i in range(groupCount):
        groupUserList = []


        for j in range(len(dfInt.index)):
            if dfInt.iloc[j]['groupID'] == i:
                groupUserList.append(dfInt.iloc[j]['userID'])



        print(groupUserList)
        print('testtesttest')
        print(dfInterests)
        results = results.append(pd.DataFrame([['NormalKmeans', loopNo + 1, len(groupUserList),
                                                calcIntCosSim(groupUserList, dfInterests, True),
                                                calcIntCosSim(groupUserList, dfInterests, False),
                                                calcTopIntRatio(groupUserList, dfInterests),
                                                calcIntJaccard(groupUserList, dfInterests)]], columns=results.columns))
        # print(results)

        tempResults = poi2groupOP('NormalKmeans', dfNodesAvg, dfInterests, groupUserList, startNode, endNode, budget, day,
                                  visitedNodePerUsr)
        # tempResults['cluster'] = 'kMeans'
        tempResults['iter'] = loopNo + 1
        tempResults['groupID'] = i + 1
        resultsPOI2GroupNormalKmean = resultsPOI2GroupNormalKmean.append(tempResults)
    print(resultsPOI2GroupNormalKmean)



    # record start time
    kmeanstime = time.time()

    # kmeans clustering
    dfIntDropID = dfInterests.drop(['userID'], axis=1)
    dfInt = dfInterests.copy()
    kmeans = KMeans(n_clusters=groupCount, random_state=0).fit(dfInt[['Cultural','Amusement', 'Shopping', 'Structure', 'Sport', 'Beach' ]])
    dfInt['groupID'] =  kmeans.labels_
    dfInt = dfInt.sort_values(['groupID'], ascending = True)
    currentID = 0

    dfIntDropID.to_csv('dfInt_exUserID.csv', header=None, index=False, sep='\t', encoding='utf-8')


    clusters = run('dfInt_exUserID.csv', 'link.constraints', 5, 10, 300, 1e-4)

    for i in range(groupCount):
        groupUserList = []



        with open('file.csv', 'r') as f:
            sentence_list = [[s.strip()] for s in f]
            groupUserList = [v.rstrip().split(",") for v in sentence_list[i]]
            groupUserList = [j for sub in groupUserList for j in sub]
            print(groupUserList)
        dfInterests = pd.read_csv('dfInterests150Ori.csv', sep=";")


        print(groupUserList)
        print(dfInterests)
        results = results.append(pd.DataFrame([['CCKmeans', loopNo + 1, len(groupUserList),
                                                calcIntCosSim(groupUserList, dfInterests, True),
                                                calcIntCosSim(groupUserList, dfInterests, False),
                                                calcTopIntRatio(groupUserList, dfInterests),
                                                calcIntJaccard(groupUserList, dfInterests)]], columns=results.columns))
        #print(results)

        tempResults = poi2groupOP('CCKmeans', dfNodesAvg, dfInterests, groupUserList, startNode, endNode, budget, day, visitedNodePerUsr)
        # tempResults['cluster'] = 'kMeans'
        tempResults['iter'] = loopNo + 1
        tempResults['groupID'] = i + 1
        resultsPOI2GroupKmean = resultsPOI2GroupKmean.append(tempResults)

    # calcualte running time for kmeans clustering
    kmeanstime = time.time() - kmeanstime
    print(resultsPOI2GroupKmean)


    resultsPOI2Group = resultsPOI2Group.append(resultPOI2GroupRan, sort=False)
    resultsPOI2Group = resultsPOI2Group.append(resultsPOI2GroupRanByDay, sort=False)

    resultsPOI2Group = resultsPOI2Group.append(resultsPOI2GroupNormalKmean, sort=False)

    resultsPOI2Group = resultsPOI2Group.append(resultsPOI2GroupKmean, sort=False)
    resultsPOI2Group = resultsPOI2Group.reset_index(drop=True)
    results = results.reset_index(drop=True)

    # create new dataframe to do the Average results statistic
    temStatResults = pd.DataFrame()
    temStatResults = temStatResults.append(resultPOI2GroupRan, sort=False)
    temStatResults = temStatResults.append(resultsPOI2GroupRanByDay, sort=False)

    temStatResults = temStatResults.append(resultsPOI2GroupNormalKmean, sort=False)

    temStatResults = temStatResults.append(resultsPOI2GroupKmean, sort=False)
    print(temStatResults)

    print(resultsPOI2Group.to_string())
    print(resultsPOI2GroupNormalKmean)
    print(results)

    resultsMeanTem = calMean(temStatResults, budget, startNode, loopNo,
                             num_of_user_to_select)  # various statistic calculation
    resultsMean = resultsMean.append(resultsMeanTem)

resultsPOI2Group.to_csv('4ClusterMethodIn5Loops.csv', index=False, encoding='utf-8')  # save the original results
results.to_csv('4ClusterMethodIn5Loops_statistics_200.csv', index=False,
               encoding='utf-8')  # save the statistics calculation for groups
resultsMean.to_csv('4ClusterMethodIn5Loops_average_200.csv', index=False,
                   encoding='utf-8')  # save the average statistics results

# resultsMean.to_csv('resultsMean.csv', sep='\t', encoding='utf-8')

# print(dfInterests.to_string())
# print(dfNodesAvg)
# print('random once exc time: ' + str(rantime))
# print('random per day exc time: ' + str(ranPerDaytime))
# print('kmeans exc time: ' + str(kmeanstime))

