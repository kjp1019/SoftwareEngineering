import csv
import mysql.connector
from datetime import datetime

# MySQL 연결 설정
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1221",
    database="sw_wordtest"
)
cursor = conn.cursor()

# CSV 파일 읽기
with open('engword_final.csv', 'r', encoding='utf-8') as file:
    csv_reader = csv.reader(file)
    next(csv_reader)  # 헤더 건너뛰기
    
    # 각 행 처리
    for row in csv_reader:
        if not row[1]:  # 빈 행 건너뛰기 (영단어가 없으면)
            continue
            
        # SQL 쿼리 실행
        sql = """
        INSERT INTO vocabulary_word 
        (english, korean, part_of_speech, difficulty, created_at, updated_at, 
         example_sentence, example_translation, is_bookmarked)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            row[1],  # english
            row[2],  # korean
            row[3],  # part_of_speech
            row[4],  # difficulty
            row[5],  # created_at
            row[6],  # updated_at
            row[7],  # example_sentence
            row[8],  # example_translation
            False    # is_bookmarked 기본값
        )
        
        try:
            cursor.execute(sql, values)
            print(f"Added word: {row[1]} - {row[2]}")
        except mysql.connector.Error as err:
            print(f"Error adding word {row[1]}: {err}")

# 변경사항 저장
conn.commit()

# 연결 종료
cursor.close()
conn.close()

print("데이터 임포트가 완료되었습니다.") 