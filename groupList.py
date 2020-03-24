import pandas as pd
import csv
def groupUserListProcess(clusters):
    print(clusters)
    userID = pd.read_csv('userID.csv', sep=";", names=['userID'])
    dfclusters = pd.DataFrame(clusters, columns = ['groupNO'])

    print(dfclusters)

    dfML = pd.read_csv('mustLink.csv', sep=";")
    print(dfML)
    dfInterests = pd.read_csv('dfInterests150Ori.csv', sep=";")
    print(dfInterests.to_string())
    idList1 = dfML['userID1'].tolist()
    idList2 = dfML['userID2'].tolist()
    joinedlist = idList1 + idList2
    joinedlist.sort()
    print(joinedlist)


    bonusUser = []
    for i in joinedlist:
        x = dfInterests.loc[i]['userID']
        bonusUser.append(x)
        print(x)
    print(bonusUser)

    dfbonusUser = pd.DataFrame(bonusUser, columns=['userID'])
    print(dfbonusUser)
    dfbonusUser.to_csv('dfbonusUser.csv', index=False, sep=';', encoding='utf-8')


    result = pd.concat([dfclusters, userID], axis=1)
    print(result.to_string())
    resultSort = result.sort_values(by=['groupNO'])
    print(resultSort.to_string())

    groupList1, groupList2, groupList3, groupList4, groupList5 = ([] for i in range(5))
    for index, row in result.iterrows():
            if row['groupNO'] == 0:
                groupList1.append(row['userID'])
            if row['groupNO'] == 1:
                groupList2.append(row['userID'])
            if row['groupNO'] == 2:
                groupList3.append(row['userID'])
            if row['groupNO'] == 3:
                groupList4.append(row['userID'])
            if row['groupNO'] == 4:
                groupList5.append(row['userID'])
    print(groupList1)
    print(groupList2)
    print(groupList3)
    print(groupList4)
    print(groupList5)



    with open('file.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(groupList1)
        writer.writerow(groupList2)
        writer.writerow(groupList3)
        writer.writerow(groupList4)
        writer.writerow(groupList5)

    with open('file.csv', 'r') as f:
        sentence_list = [[s.strip()] for s in f]
        newl = [v.rstrip().split(",") for v in sentence_list[0]]
        newl = [j for sub in newl for j in sub]
        print(newl)



