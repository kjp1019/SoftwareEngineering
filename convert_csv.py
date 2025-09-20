import csv

def csv_to_sql():
    with open('/Users/kenny/desktop/sw_wordDB.csv', 'r') as f:
        reader = csv.DictReader(f)
        with open('import.sql', 'w') as out:
            out.write('SET FOREIGN_KEY_CHECKS=0;\n')
            for row in reader:
                sql = f'''INSERT INTO vocabulary_word 
                        (id, english, korean, part_of_speech, difficulty, created_at, updated_at, example_sentence, example_translation)
                        VALUES 
                        ({row['id']}, "{row['english']}", "{row['korean']}", "{row['part_of_speech']}", 
                        "{row['difficulty']}", "{row['created_at']}", "{row['updated_at']}",
                        "{row['example_sentence'].replace('"', '""')}", "{row['example_translation'].replace('"', '""')}");'''
                out.write(sql + '\n')
            out.write('SET FOREIGN_KEY_CHECKS=1;\n')

if __name__ == '__main__':
    csv_to_sql() 