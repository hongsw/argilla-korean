#!/usr/bin/env python3
"""
Argilla 데이터를 JSONL 형식으로 내보내기 - 개선된 버전
response values에서 라벨을 정확히 추출
"""

import json
from datetime import datetime
import os
import subprocess

def export_dataset_to_jsonl_v2(dataset_name='kor_fin2'):
    """Docker exec를 통해 데이터를 추출하여 JSONL로 저장 - 개선된 버전"""
    
    timestamp = datetime.now().strftime("%Y%m%d")
    output_file = f"{dataset_name}_{timestamp}_2.jsonl"
    
    print(f"📥 데이터셋 '{dataset_name}' 추출 시작 (v2)...")
    
    # Docker exec로 데이터 추출 - 더 정확한 쿼리
    cmd = [
        'docker', 'exec', 'argilla-korean-postgres-1',
        'psql', '-U', 'postgres', '-d', 'argilla',
        '-t', '-A',
        '-c', f"""
        SELECT json_build_object(
            'id', r.id,
            'text', r.fields->>'text',
            'status', r.status,
            'metadata', r.metadata,
            'external_id', r.external_id,
            'created_at', r.inserted_at,
            'updated_at', r.updated_at,
            'response_id', resp.id,
            'response_values', resp.values,
            'response_status', resp.status,
            'response_user', resp.user_id,
            'response_date', resp.inserted_at
        )
        FROM records r
        JOIN datasets d ON r.dataset_id = d.id
        LEFT JOIN responses resp ON resp.record_id = r.id
        WHERE d.name = '{dataset_name}'
        ORDER BY r.id, resp.id;
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
        processed_ids = set()  # 중복 제거용
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for line in lines:
                if line.strip():
                    try:
                        # PostgreSQL JSON 출력을 파싱
                        record = json.loads(line)
                        
                        # 중복 제거 (같은 record_id는 한 번만)
                        record_id = record.get('id')
                        if record_id in processed_ids and not record.get('response_id'):
                            continue
                        
                        # JSONL 형식으로 정리
                        jsonl_record = {
                            'id': record_id,
                            'text': record.get('text', ''),
                            'label': None,
                            'metadata': record.get('metadata', {}),
                            'status': record.get('status'),
                            'created_at': record.get('created_at'),
                            'updated_at': record.get('updated_at')
                        }
                        
                        # response_values에서 라벨 추출
                        if record.get('response_values'):
                            response_values = record.get('response_values')
                            
                            # "라벨_0" 키에서 값 추출
                            if '라벨_0' in response_values:
                                label_obj = response_values['라벨_0']
                                if isinstance(label_obj, dict) and 'value' in label_obj:
                                    jsonl_record['label'] = label_obj['value']
                            # 다른 가능한 키들도 체크
                            elif 'label_0' in response_values:
                                label_obj = response_values['label_0']
                                if isinstance(label_obj, dict) and 'value' in label_obj:
                                    jsonl_record['label'] = label_obj['value']
                            else:
                                # 첫 번째 키-값 쌍에서 시도
                                for key, value in response_values.items():
                                    if isinstance(value, dict) and 'value' in value:
                                        jsonl_record['label'] = value['value']
                                        break
                                    elif isinstance(value, str):
                                        jsonl_record['label'] = value
                                        break
                            
                            jsonl_record['annotator'] = record.get('response_user')
                            jsonl_record['annotation_date'] = record.get('response_date')
                            jsonl_record['response_status'] = record.get('response_status')
                        
                        # 이미 처리한 레코드인지 확인
                        if record_id not in processed_ids or record.get('response_id'):
                            # JSONL 라인으로 저장
                            f.write(json.dumps(jsonl_record, ensure_ascii=False) + '\n')
                            records_written += 1
                            processed_ids.add(record_id)
                        
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON 파싱 오류 (스킵): {e}")
                        continue
                    except Exception as e:
                        print(f"⚠️ 처리 오류 (스킵): {e}")
                        continue
        
        print(f"✅ JSONL 파일 생성 완료: {output_file}")
        print(f"📊 총 {records_written}개 레코드 저장됨")
        
        # 파일 크기 확인
        file_size = os.path.getsize(output_file)
        print(f"📦 파일 크기: {file_size / 1024:.2f} KB")
        
        # 샘플 출력
        print(f"\n📄 샘플 (처음 5줄):")
        with open(output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 5:
                    break
                record = json.loads(line)
                text_preview = record.get('text', '')[:50]
                label = record.get('label', 'None')
                print(f"  {i+1}. Text: {text_preview}..., Label: {label}")
        
        # 라벨 통계
        print(f"\n📊 라벨 통계:")
        label_counts = {}
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                record = json.loads(line)
                label = record.get('label')
                if label:
                    label_counts[label] = label_counts.get(label, 0) + 1
        
        for label, count in sorted(label_counts.items()):
            print(f"  - {label}: {count}개")
        
        if not label_counts:
            print("  - 라벨이 있는 레코드가 없습니다.")
        
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
    print("🚀 Argilla 데이터 JSONL 내보내기 v2")
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
            export_dataset_to_jsonl_v2(dataset_name)
        else:
            print(f"❌ 데이터셋 '{dataset_name}'을 찾을 수 없습니다.")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 데이터셋 목록 조회 실패: {e}")

if __name__ == "__main__":
    main()