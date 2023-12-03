######################################         <(YOUTUBE DATA HARVESING AND WAREHOUSING)>         ##################################################

# pip install streamlit
# pip install pandas
# pip install google-api-python-client
# pip install mysql-connector-python
# pip install pymongo

# import all package
import streamlit as st
import pandas as pd
import pymongo
import mysql.connector
from mysql.connector import Error , connect 
from googleapiclient.discovery import build

# Youtube Api connection function
def api_connect():
  api_service_name='youtube'
  api_version='v3'
  api_key="AIzaSyDLST8XdCShB7im8iBNNqzIaHPT9RUKEho"
  youtube=build(api_service_name,api_version,developerKey=api_key)
  return youtube

youtube=api_connect()

# creating a database and connnection string
def create_db():
  mydb=mysql.connector.connect(host="localhost",port="3306",user='ajith',password="Ajith@24")
  cursor=mydb.cursor()
  create_db="CREATE DATABASE IF NOT EXISTS youtube;"
  try:
    with mydb:
      cursor.execute(create_db)
      mydb.commit()
  except Error as e:
      print("Error:", e)
  finally:
      if mydb:
          mydb.close()

# calling the database creation function
create_db()

# get youtube channel info
def get_channel_info(channel_id):
  request=youtube.channels().list(
      part='snippet,ContentDetails,statistics,status',
      id=channel_id
  )
  response=request.execute()

  for item in response['items']:
    data=dict(channel_id=item['id'],
              channel_name=item['snippet']['title'],
              subscribers=item['statistics']['subscriberCount'],
              views=item['statistics']['viewCount'],
              total_videos=item['statistics']['videoCount'],
              channel_description=item['snippet']['description'],
              channel_status=item['status']['privacyStatus'],
              playlist_id=item['contentDetails']['relatedPlaylists']['uploads'])
  return data

# Get channel video ids
def get_video_ids(channel_id):
  video_ids=[]
  response=youtube.channels().list(id=channel_id,part='contentDetails').execute()
  playlist_id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
  next_page_token=None

  while True:
    response1=youtube.playlistItems().list(part='snippet',playlistId=playlist_id,maxResults=50,pageToken=next_page_token).execute()

    for i in range(len(response1['items'])):
      video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])

    next_page_token=response1.get('nextPageToken')

    if next_page_token is None:
      break
  return video_ids

# get video info
def get_video_info(video_ids):
  video_data = []
  for video_id in video_ids:
    request=youtube.videos().list(part='snippet,ContentDetails,statistics',id=video_id)
    response=request.execute()
    def time_duration(t):
      a = pd.Timedelta(t)
      b = str(a).split()[-1]
      return b

    for item in response['items']:
      data=dict(channel_name=item['snippet']['channelTitle'],
                channel_id=item['snippet']['channelId'],
                video_id=item['id'],
                title=item['snippet']['title'],
                description=item['snippet'].get('description'),
                published_date=item['snippet']['publishedAt'],
                views=item['statistics'].get('viewCount'),
                likes=item['statistics'].get('likeCount'),
                favorite=item['statistics'].get('favoriteCount'),
                comments=item['statistics'].get('commentCount'),
                duration=time_duration(item['contentDetails']['duration']),
                thumbnail=item['snippet']['thumbnails']['default'].get('url'),
                definition=item['contentDetails']['definition'],
                caption=item['contentDetails']['caption']
                )
      video_data.append(data)
  return video_data

# get comment details
def get_comment_info(video_ids):
  comment_data = []
  try:
    for video_id in video_ids:
      request=youtube.commentThreads().list(part='snippet',videoId=video_id,maxResults=50)
      response=request.execute()

      for item in response['items']:
        data=dict(commentid=item['snippet']['topLevelComment']['id'],
                  videoid=item['snippet']['topLevelComment']['snippet']['videoId'],
                  comment_text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                  comment_author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                  comment_time=item['snippet']['topLevelComment']['snippet']['publishedAt']
                  )
        comment_data.append(data)
  except:
    pass
  return comment_data

# get playlist info
def get_playlist_info(channel_id):
  playlist_data=[]
  next_page_token=None
  while True:
    request=youtube.playlists().list(part='snippet,contentDetails',channelId=channel_id,maxResults=50,pageToken=next_page_token)
    response=request.execute()

    for item in response['items']:
      data=dict(playlist_id=item['id'],
                channel_id=item['snippet']['channelId'],
                title=item['snippet']['title'],
                publishedat=item['snippet']['publishedAt'],
                video_count=item['contentDetails']['itemCount']
                )
      playlist_data.append(data)
    next_page_token=response.get('nextPageToken')
    if next_page_token is None:
        break
  return playlist_data

# Mongodb connection string
mongo_client=pymongo.MongoClient("mongodb+srv://ajith:Ajith24@myatlasclusteredu.43hutqm.mongodb.net/?retryWrites=true&w=majority")
db=mongo_client['youtube_data']

# upload youtube data to mongodb data lake
def mongo_upload(channel_id):
  chl_details=get_channel_info(channel_id)
  vid_ids=get_video_ids(channel_id)
  vid_details=get_video_info(vid_ids)
  plst_details=get_playlist_info(channel_id)
  cmt_details=get_comment_info(vid_ids)

  col1=db["channel_details"]
  col1.insert_one({"channel_info":chl_details,"playlist_details":plst_details,"video_details":vid_details,"comment_details":cmt_details})

  return "Data Uploaded"

# create table channel
def channel_table():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="ajith",
            password="Ajith@24",
            database="youtube"
        )
        cursor = mydb.cursor()

        channel_query = '''
        CREATE TABLE IF NOT EXISTS channels (
            id int auto_increment primary key,
            channel_id varchar(100) not null unique,
            channel_name varchar(250) not null,
            subscribers int,
            channel_views bigint,
            total_videos int,
            channel_description TEXT,
            channel_status varchar(250),
            playlist_id varchar(100)
        );
        '''
        cursor.execute(channel_query)
        mydb.commit()

        db = mongo_client['youtube_data']
        col = db['channel_details']
        channel_data = []
        
        for data in col.find({}, {"_id": 0, "channel_info": 1}):
            channel_data.append(data["channel_info"])
        
        df = pd.DataFrame(channel_data)

        insert_query = '''
        INSERT IGNORE INTO channels 
        (channel_id, channel_name, subscribers, channel_views, total_videos, channel_description, channel_status, playlist_id) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        '''

        # Convert DataFrame to list of tuples for bulk insertion
        values = [tuple(row) for row in df.values]

        # Bulk insert data into the table
        with mydb:
            cursor.executemany(insert_query, values)
            mydb.commit()

    except Error as e:
        print("Error:", e)
    finally:
        if mydb:
            mydb.close()

# create table playlist
def playlist_table():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="ajith",
            password="Ajith@24",
            database="youtube",
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        
        cursor = mydb.cursor()

        # Create the playlist table
        playlist = '''
        CREATE TABLE IF NOT EXISTS playlist (
            id int auto_increment primary key,
            playlist_id varchar(100) not null unique,
            channel_id varchar(100),
            playlist_name varchar(250),
            published_date datetime,
            video_count int,
            foreign key (channel_id) references channels(channel_id)
        );
        '''

        cursor.execute(playlist)
        mydb.commit()

        # Retrieve data from MongoDB and insert into MySQL
        db = mongo_client['youtube_data']
        playlist_data = []
        col = db['channel_details']
        
        for data in col.find({}, {"_id": 0, "playlist_details": 1}):
            for i in range(len(data["playlist_details"])):
                playlist_data.append(data["playlist_details"][i])
        
        df = pd.DataFrame(playlist_data)

        for index, row in df.iterrows():
            insert_query = '''
            INSERT IGNORE INTO playlist (playlist_id, channel_id, playlist_name, published_date, video_count)
            VALUES (%s, %s, %s, %s, %s)
            '''
            values=(
                row['playlist_id'],
                row['channel_id'],
                row['title'],
                row['publishedat'],
                row['video_count'])
            
            cursor.execute(insert_query, values)
            mydb.commit()

    except Error as e:
        print("Error:", e)
    finally:
        if mydb:
            mydb.close()

# create video table
def video_table():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="ajith",
            password="Ajith@24",
            database="youtube"
        )
        cursor = mydb.cursor()

        video_query = '''
        CREATE TABLE IF NOT EXISTS video (
            id int auto_increment primary key,
            channel_name varchar(250),
            channel_id varchar(100),
            video_id varchar(100) not null unique,
            video_name varchar(250),
            video_description TEXT,
            published_date datetime,
            views int,
            likes int,
            favorite_count int,
            comments int,
            duration TIME,
            thumbnail varchar(250),
            definition varchar(250),
            caption varchar(250),
            foreign key (channel_id) references channels(channel_id)
        );
        '''

        cursor.execute(video_query)
        mydb.commit()
        # Retrieve data from MongoDB and insert into MySQL
        db = mongo_client['youtube_data']
        video_data = []
        col = db['channel_details']

        for data in col.find({}, {"_id": 0, "video_details": 1}):
            for i in range(len(data["video_details"])):
                video_data.append(data["video_details"][i])
        df = pd.DataFrame(video_data)

        for index, row in df.iterrows():
                insert_query = '''
                INSERT IGNORE INTO video (channel_name, channel_id, video_id, video_name, video_description, published_date, views, likes, favorite_count, comments, duration, thumbnail, definition, caption)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                '''
                values=(
                    row['channel_name'],
                    row['channel_id'],
                    row['video_id'],
                    row['title'],
                    row['description'],
                    row['published_date'],
                    row['views'],
                    row['likes'],
                    row['favorite'],
                    row['comments'],
                    row['duration'],
                    row['thumbnail'],
                    row['definition'],
                    row['caption'])
                
                cursor.execute(insert_query, values)
                mydb.commit()   
    except Error as e:
        print("Error:", e)
    finally:
        if mydb:
            mydb.close()

# create a comment table
def comment_table():
    try:
        mydb = mysql.connector.connect(
            host="localhost",
            port="3306",
            user="ajith",
            password="Ajith@24",
            database="youtube"
        )
        cursor = mydb.cursor()

        comment='''CREATE TABLE IF NOT EXISTS comment (id int auto_increment primary key,
        comment_id varchar(100) unique,
        video_id varchar(100),
        comment_text TEXT,
        comment_author varchar(250),
        comment_time datetime,foreign key (video_id) references video(video_id));'''

        cursor.execute(comment)
        mydb.commit()

        # Retrieve data from MongoDB and insert into MySQL
        db = mongo_client['youtube_data']
        comment_data = []
        col = db['channel_details']

        for data in col.find({}, {"_id": 0, "comment_details": 1}):
            for i in range(len(data["comment_details"])):
                comment_data.append(data["comment_details"][i])
        df = pd.DataFrame(comment_data)

        for index, row in df.iterrows():
            insert_query = '''
            INSERT IGNORE INTO comment (comment_id, video_id, comment_text, comment_author, comment_time)
            VALUES (%s, %s, %s, %s, %s)
            '''
            values=(
                row['commentid'],
                row['videoid'],
                row['comment_text'],
                row['comment_author'],
                row['comment_time'])
            
            cursor.execute(insert_query, values)
            mydb.commit()

    except Error as e:
        print("Error:", e)
    finally:
        if mydb:
            mydb.close()

# upload data to mysql database
def mysql_upload():
    channel_table()
    playlist_table()
    video_table()
    comment_table()
    
    return "Data Uploaded"

# show channel details in the webpage
def show_channel_info():
    db = mongo_client['youtube_data']
    col = db['channel_details']
    channel_data = []

    for data in col.find({}, {"_id": 0, "channel_info": 1}):
        channel_data.append(data["channel_info"])

    df = st.dataframe(channel_data)

    return df

# show comment details in the webpage
def show_playlist_info():
    db = mongo_client['youtube_data']
    col = db['channel_details']
    playlist_data = []

    for data in col.find({}, {"_id": 0, "playlist_details": 1}):
        for i in range(len(data["playlist_details"])):
            playlist_data.append(data["playlist_details"][i])

    df = st.dataframe(playlist_data)

    return df

# show video details in the webpage
def show_video_info():
    db = mongo_client['youtube_data']
    col = db['channel_details']
    video_data = []

    for data in col.find({}, {"_id": 0, "video_details": 1}):
        for i in range(len(data["video_details"])):
            video_data.append(data["video_details"][i])

    df = st.dataframe(video_data)

    return df

# show comment details in the webpage
def show_comment_info():
    db = mongo_client['youtube_data']
    col = db['channel_details']
    comment_data = []

    for data in col.find({}, {"_id": 0, "comment_details": 1}):
        for i in range(len(data["comment_details"])):
            comment_data.append(data["comment_details"][i])

    df = st.dataframe(comment_data)

    return df

# stramlit application
st.title("Youtube Data Analysis")
st.subheader("Upload youtube channel id")
channel_id = st.text_input("Enter channel id")
# st.button("Submit")
#st.button("Download Data for preview")

if st.button("Submit"):
    channel_ids=[]
    db = mongo_client['youtube_data']
    col = db['channel_details']
    for data in col.find({}, {"_id": 0, "channel_info": 1}):
        channel_ids.append(data["channel_info"]["channel_id"])
    if channel_id in channel_ids:
        st.success("Channel id already exists")
    else:
        insert= mongo_upload(channel_id)
        st.success(insert)
        st.balloons()
    pass

if st.button("Download Data for preview"):
    table=mysql_upload()
    st.success(table)
    st.balloons()
    pass

show_tables=st.radio("Select Data", ("Channel Details", "Video Details", "Playlist Details", "Comment Details"))

if show_tables=="Channel Details":
    show_channel_info()
elif show_tables=="Video Details":
    show_video_info()
elif show_tables=="Playlist Details":
    show_playlist_info()
elif show_tables=="Comment Details":
    show_comment_info()

# sql queries for questions
def analysis(question):
    mydb=mysql.connector.connect(host="localhost",port="3306",user='ajith',password="Ajith@24",database="youtube")
    cursor=mydb.cursor()
    cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';")
    mydb.commit()

    q1= "1. What are the names of all the videos and their corresponding channels?"
    q2= "2. Which channels have the most number of videos, and how many videos do they have?"
    q3= "3. What are the top 10 most viewed videos and their respective channels?"
    q4= "4. How many comments were made on each video, and what are their corresponding video names?"
    q5= "5. Which videos have the highest number of likes, and what are their corresponding channel names?"
    q6= "6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?"
    q7= "7. What is the total number of views for each channel, and what are their corresponding channel names?"
    q8= "8. What are the names of all the channels that have published videos in the year 2022?"
    q9= "9. What is the average duration of all videos in each channel, and what are their corresponding channel names?"
    q10= "10. Which videos have the highest number of comments, and what are their corresponding channel names?"

    query1= "select video_name, channel_name from video;"
    query2= "select channel_name, total_videos from channels order by total_videos desc;"
    query3= "select video_name, channel_name from video order by views desc limit 10;"
    query4= "select video_name, comments from video order by comments desc;"
    query5= "select video_name,  likes , channel_name from video order by likes desc limit 1;"
    query6= "select video_name, likes, channel_name from video order by likes desc;"
    query7= "select channel_name, channel_views from channels order by channel_views desc;"
    query8= "select channel_name , published_date from video where year(published_date) = 2022;"
    query9= "select channel_name, sec_to_time(avg(time_to_sec(duration))) average_duration from video group by channel_name;"
    query10= "select video_name, channel_name, comments ,rank() over(order by comments desc) as Rank_no from video limit 10;"

    try:
        if question == q1:
            cursor.execute(query1)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['video_name', 'channel_name'])
            st.write(df)

        elif question == q2:
            cursor.execute(query2)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['channel_name', 'total_videos'])
            st.write(df)

        elif question == q3:
            cursor.execute(query3)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['video_name', 'channel_name'])
            st.write(df)

        elif question == q4:
            cursor.execute(query4)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['video_name', 'comment_count'])
            st.write(df)

        elif question == q5:
            cursor.execute(query5)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['video_name', 'likes', 'channel_name'])
            st.write(df)

        elif question == q6:
            cursor.execute(query6)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['video_name', 'likes', 'channel_name'])
            st.write(df)

        elif question == q7:
            cursor.execute(query7)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['channel_name', 'channel_views'])
            st.write(df)

        elif question == q8:
            cursor.execute(query8)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['channel_name', 'published_date'])
            st.write(df)

        elif question == q9:
            cursor.execute(query9)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['channel_name', 'average_duration'])
            d9 =[]
            for index,row in df.iterrows():
                channel_name = row['channel_name']
                average_duration = row['average_duration']
                average_duration_str= str(average_duration)
                d9.append(dict(channel_name=channel_name, average_duration=average_duration_str))
            df = pd.DataFrame(d9)
            st.write(df)

        elif question == q10:
            cursor.execute(query10)
            data = cursor.fetchall()
            mydb.commit()
            df = pd.DataFrame(data, columns=['video_name', 'channel_name', 'comments', 'Rank_no'])
            st.write(df)
    except:
        st.error('Click download data button to see the results')

# sql Analysis questions
q1= "1. What are the names of all the videos and their corresponding channels?"
q2= "2. Which channels have the most number of videos, and how many videos do they have?"
q3= "3. What are the top 10 most viewed videos and their respective channels?"
q4= "4. How many comments were made on each video, and what are their corresponding video names?"
q5= "5. Which videos have the highest number of likes, and what are their corresponding channel names?"
q6= "6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?"
q7= "7. What is the total number of views for each channel, and what are their corresponding channel names?"
q8= "8. What are the names of all the channels that have published videos in the year 2022?"
q9= "9. What is the average duration of all videos in each channel, and what are their corresponding channel names?"
q10= "10. Which videos have the highest number of comments, and what are their corresponding channel names?"

question = st.selectbox("Select Question", (q1, q2, q3, q4, q5, q6, q7, q8, q9, q10))
analysis(question)
