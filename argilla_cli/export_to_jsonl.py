#!/usr/bin/env python3
"""
Argilla 데이터를 JSONL 형식으로 내보내기
각 레코드를 한 줄의 JSON으로 저장
"""

import json
from datetime import datetime
import os
import subprocess

def export_dataset_to_jsonl_via_docker(dataset_name='kor_fin2'):
    """Docker exec를 통해 데이터를 추출하여 JSONL로 저장"""
    
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = f"{dataset_name}_{timestamp}.jsonl"
    
    print(f"📥 데이터셋 '{dataset_name}' 추출 시작...")
    
    # SQL 쿼리 작성
    sql_query = f"""
    SELECT 
        r.id as record_id,
        r.status,
        r.inserted_at,
        r.updated_at,
        -- fields (JSON 필드들)
        f.name as field_name,
        f.title as field_title,
        r.fields as record_fields,
        -- responses
        resp.id as response_id,
        resp.values as response_values,
        resp.status as response_status,
        resp.user_id,
        resp.inserted_at as response_date,
        -- questions
        q.name as question_name,
        q.title as question_title,
        q.settings as question_settings,
        -- dataset info
        d.name as dataset_name,
        d.guidelines as dataset_guidelines
    FROM records r
    JOIN datasets d ON r.dataset_id = d.id
    LEFT JOIN fields f ON f.dataset_id = d.id
    LEFT JOIN responses resp ON resp.record_id = r.id
    LEFT JOIN questions q ON q.dataset_id = d.id
    WHERE d.name = '{dataset_name}'
    ORDER BY r.id, resp.id;
    """
    
    # PostgreSQL에서 데이터 추출
    import subprocess
    
    # 더 간단한 쿼리로 시작
    simple_query = f"""
    COPY (
        SELECT 
            r.id,
            r.status,
            r.fields,
            r.metadata,
            r.external_id,
            r.inserted_at,
            r.updated_at,
            resp.values as response_values,
            resp.status as response_status,
            resp.user_id as response_user,
            resp.inserted_at as response_date
        FROM records r
        JOIN datasets d ON r.dataset_id = d.id
        LEFT JOIN responses resp ON resp.record_id = r.id
        WHERE d.name = '{dataset_name}'
        ORDER BY r.id, resp.id
    ) TO STDOUT WITH (FORMAT CSV, HEADER TRUE, DELIMITER E'\\t');
    """
    
    # Docker exec로 데이터 추출 - 더 간단한 쿼리 사용
    cmd = [
        'docker', 'exec', 'argilla-korean-postgres-1',
        'psql', '-U', 'postgres', '-d', 'argilla',
        '-t', '-A',
        '-c', f"""
        SELECT row_to_json(t)
        FROM (
            SELECT 
                r.id,
                r.status,
                r.fields::text as fields_text,
                r.metadata::text as metadata_text,
                r.external_id,
                r.inserted_at,
                r.updated_at,
                resp.values::text as response_values,
                resp.status as response_status,
                resp.user_id as response_user,
                resp.inserted_at as response_date
            FROM records r
            JOIN datasets d ON r.dataset_id = d.id
            LEFT JOIN responses resp ON resp.record_id = r.id
            WHERE d.name = '{dataset_name}'
            ORDER BY r.id, resp.id
        ) t;
        """
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.returncode != 0:
            print(f"❌ 데이터 추출 실패: {result.stderr}")
            return False
        
        # JSONL 파일로 저장
        lines = result.stdout.strip().split('\n')
        records_written = 0
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in lines:
                if line.strip():
                    try:
                        # PostgreSQL JSON 출력을 파싱
                        record = json.loads(line)
                        
                        # fields_text를 JSON으로 파싱
                        fields = {}
                        if record.get('fields_text'):
                            try:
                                fields = json.loads(record['fields_text'])
                            except:
                                fields = {}
                        
                        # metadata_text를 JSON으로 파싱
                        metadata = {}
                        if record.get('metadata_text'):
                            try:
                                metadata = json.loads(record['metadata_text'])
                            except:
                                metadata = {}
                        
                        # JSONL 형식으로 정리
                        jsonl_record = {
                            'id': record.get('id'),
                            'text': fields.get('text', ''),
                            'label': None,
                            'metadata': metadata,
                            'status': record.get('status'),
                            'created_at': record.get('inserted_at'),
                            'updated_at': record.get('updated_at')
                        }
                        
                        # 응답에서 라벨 추출
                        if record.get('response_values'):
                            try:
                                response_values = json.loads(record['response_values'])
                                # label_selection 또는 sentiment 등의 키 찾기
                                for key in ['label_selection', 'sentiment', 'label', 'labels']:
                                    if key in response_values:
                                        value = response_values[key]
                                        if isinstance(value, dict):
                                            jsonl_record['label'] = value.get('value')
                                        else:
                                            jsonl_record['label'] = value
                                        break
                                
                                jsonl_record['annotator'] = record.get('response_user')
                                jsonl_record['annotation_date'] = record.get('response_date')
                            except:
                                pass
                        
                        # JSONL 라인으로 저장
                        f.write(json.dumps(jsonl_record, ensure_ascii=False) + '\n')
                        records_written += 1
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON 파싱 오류 (스킵): {e}")
                        continue
        
        print(f"✅ JSONL 파일 생성 완료: {output_file}")
        print(f"📊 총 {records_written}개 레코드 저장됨")
        
        # 파일 크기 확인
        file_size = os.path.getsize(output_file)
        print(f"📦 파일 크기: {file_size / 1024:.2f} KB")
        
        # 샘플 출력
        print(f"\n📄 샘플 (처음 3줄):")
        with open(output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                record = json.loads(line)
                print(f"  {i+1}. ID: {record.get('id')}, Text: {record.get('text', '')[:50]}..., Label: {record.get('label')}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Docker 명령 실행 실패: {e}")
        print(f"에러 출력: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("🚀 Argilla 데이터 JSONL 내보내기")
    print("=" * 60)
    
    # 사용 가능한 데이터셋 확인
    cmd = [
        'docker', 'exec', 'argilla-korean-postgres-1',
        'psql', '-U', 'postgres', '-d', 'argilla',
        '-t', '-A',
        '-c', "SELECT name FROM datasets ORDER BY name;"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        datasets = [d.strip() for d in result.stdout.strip().split('\n') if d.strip()]
        
        print("\n📊 사용 가능한 데이터셋:")
        for i, dataset in enumerate(datasets, 1):
            print(f"  {i}. {dataset}")
        
        # 기본값은 kor_fin2
        dataset_name = input(f"\n데이터셋 이름 입력 (기본값: kor_fin2): ").strip()
        if not dataset_name:
            dataset_name = 'kor_fin2'
        
        if dataset_name in datasets:
            export_dataset_to_jsonl_via_docker(dataset_name)
        else:
            print(f"❌ 데이터셋 '{dataset_name}'을 찾을 수 없습니다.")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 데이터셋 목록 조회 실패: {e}")

if __name__ == "__main__":
    main()