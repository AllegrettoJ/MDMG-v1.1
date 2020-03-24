import pandas as pd

pd.set_option('expand_frame_repr', False)

# preprocess the visiting history
def addVisitDuration(dfVisits):
    dfVisits = dfVisits.sort_values(['seqID', 'dateTaken'], ascending = False)
    poiCount = dfVisits.groupby(['seqID', 'poiID'], as_index=False).size().reset_index(name='visitFreq')
    dfVisits = dfVisits.merge(poiCount, left_on= ('seqID', 'poiID'), right_on=('seqID', 'poiID'))
    dfVisits = dfVisits[dfVisits.visitFreq > 1]
    dfVisits = dfVisits.sort_values(['seqID', 'poiID', 'dateTaken'], ascending=False)

    dfVisitsTem1 = dfVisits.drop_duplicates(subset=['seqID', 'poiID'], keep='first')
    dfVisitsTem2 = dfVisits.drop_duplicates(subset=['seqID', 'poiID'], keep='last')


    df = dfVisitsTem1.merge(dfVisitsTem2, left_on= ('seqID', 'poiID' , 'userID', 'poiTheme'), right_on=('seqID', 'poiID' , 'userID', 'poiTheme'))
    df['visitDuration'] = df['dateTaken_x'] - df['dateTaken_y']
    df = df.drop(['photoID_x', 'dateTaken_x', 'visitFreq_x', 'poiFreq_x','photoID_y', 'dateTaken_y', 'visitFreq_y', 'poiFreq_y'], axis=1)
    dfVisits = df[df.visitDuration != 0]

    dfavgDuration = dfVisits.groupby('poiID')['visitDuration'].mean().reset_index(name='avgDuration') # calculate average visiting time of each POI
    dfVisits = dfVisits.merge(dfavgDuration, left_on = 'poiID', right_on = 'poiID') # obtain users' detailed visiting info with average visiting time
    dfVisits = dfVisits.sort_values(['poiID'],ascending = True)

    #print(dfavgDuration)
    #print(dfVisits.to_string())

    return dfVisits, dfavgDuration