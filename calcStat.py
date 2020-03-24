import pandas as pd
from scipy import spatial
from scipy.spatial.distance import cosine
import sklearn.metrics
import statistics

def calMean(results, budget,startNode, iter, numOfUsr):
    resultsMean = results.groupby('algo')['totalPopInt', 'totalInterest','maxInterest', 'minInterest'].sum().reset_index()
    resultsMean.totalPopInt = resultsMean.totalPopInt/numOfUsr
    resultsMean.maxInterest = resultsMean.maxInterest / numOfUsr
    resultsMean.minInterest = resultsMean.minInterest / numOfUsr
    resultsMean.totalInterest = resultsMean.totalInterest/numOfUsr
    resultsMean['budget'] = budget
    resultsMean['startNode'] = startNode
    resultsMean['iter'] = iter + 1

    print(resultsMean.to_string())
    return resultsMean

# Calculate the cosine similarity of users in the same group [userIntGroup] based on their interests [dfInterests]
def calcIntCosSim(userIntGroup, dfInterests, binaryInt):
    cosVec =[]
    userIntByTime = pd.DataFrame(columns=dfInterests.columns)
    for i in range(len(userIntGroup)):
        userIntByTime = userIntByTime.append(dfInterests.loc[dfInterests['userID'] == userIntGroup[i]])
    userIntByTime = userIntByTime.drop(['userID'], axis=1)
    userIntByTime = userIntByTime.reset_index(drop=True)
    if binaryInt == True:
        userIntByTime[userIntByTime != 0] = 1
    for i in range(len(userIntByTime.index)):
        for j in range(len(userIntByTime.index)):
            if i != j:
                cosTem = 1 - cosine(userIntByTime.iloc[i], userIntByTime.iloc[j])
                cosVec.append(cosTem)

    cos = statistics.mean(cosVec)
    return cos

# Calculate the Jaccard similarity of users in the same group [userIntGroup] based on their interests [dfInterests]
def calcIntJaccard(userIntGroup, dfInterests):

    jacVec = []
    userIntByTime = pd.DataFrame(columns=dfInterests.columns)
    for i in range(len(userIntGroup)):
        userIntByTime = userIntByTime.append(dfInterests.loc[dfInterests['userID'] == userIntGroup[i]])
    userIntByTime = userIntByTime.drop(['userID'], axis=1)
    userIntByTime[userIntByTime != 0] = 1

    for i in range(len(userIntByTime.index)):
        for j in range(len(userIntByTime.index)):
            if i != j:
                jacTem = sklearn.metrics.jaccard_score(userIntByTime.iloc[i], userIntByTime.iloc[j])
                jacVec.append(jacTem)

    jac = statistics.mean(jacVec)
    return jac

# Calculate the largest ratio of users in the group [userIntGroup] with the same top interests in [dfInterests]
def calcTopIntRatio(userIntGroup, dfInterests):
    userIntByTime = pd.DataFrame(columns=dfInterests.columns)
    for i in range(len(userIntGroup)):
        userIntByTime = userIntByTime.append(dfInterests.loc[dfInterests['userID'] == userIntGroup[i]])
    userIntByTime = userIntByTime.drop(['userID'], axis=1)
    userIntByTime['mostInt'] = userIntByTime.idxmax(axis = 1)
    topIntCount = userIntByTime.groupby(['mostInt'], as_index=False).size().reset_index(name='Freq')
    topIntRatio = max(topIntCount['Freq'])/len(userIntByTime.index)
    return topIntRatio

