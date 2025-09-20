import csv
from django.core.management.base import BaseCommand
from apps.vocabulary.models import Word
from django.utils.timezone import make_aware
from datetime import datetime

class Command(BaseCommand):
    help = 'CSV 파일에서 단어를 가져옵니다.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='가져올 CSV 파일의 경로')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            words_created = 0
            
            for row in reader:
                # created_at과 updated_at 필드를 datetime 객체로 변환
                created_at = make_aware(datetime.strptime(row['created_at'].strip(), '%Y-%m-%d %H:%M:%S'))
                updated_at = make_aware(datetime.strptime(row['updated_at'].strip(), '%Y-%m-%d %H:%M:%S'))
                
                word, created = Word.objects.get_or_create(
                    english=row['english'].strip(),
                    defaults={
                        'korean': row['korean'].strip(),
                        'part_of_speech': row['part_of_speech'].strip(),
                        'difficulty': row['difficulty'].strip(),
                        'example_sentence': row['example_sentence'].strip() if row['example_sentence'] else '',
                        'example_translation': row['example_translation'].strip() if row['example_translation'] else '',
                        'created_at': created_at,
                        'updated_at': updated_at
                    }
                )
                
                if created:
                    words_created += 1
                    self.stdout.write(f'단어 추가됨: {word.english}')
            
            self.stdout.write(
                self.style.SUCCESS(f'성공적으로 {words_created}개의 단어를 가져왔습니다.')
            ) 