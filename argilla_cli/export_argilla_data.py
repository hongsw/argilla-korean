#!/usr/bin/env python3
"""
Argilla 데이터 내보내기 스크립트
데이터셋의 레코드와 응답을 JSON 및 CSV 형식으로 내보냅니다.
"""

import argilla as rg
import pandas as pd
import json
from datetime import datetime
import os

# Argilla 서버 연결 설정
ARGILLA_API_URL = "http://localhost:6900"
ARGILLA_API_KEY = "argilla.apikey"

def connect_to_argilla():
    """Argilla 서버에 연결"""
    try:
        rg.init(
            api_url=ARGILLA_API_URL,
            api_key=ARGILLA_API_KEY
        )
        print(f"✅ Argilla 서버에 연결되었습니다: {ARGILLA_API_URL}")
        return True
    except Exception as e:
        print(f"❌ Argilla 서버 연결 실패: {e}")
        return False

def list_datasets():
    """사용 가능한 데이터셋 목록 출력"""
    try:
        # 작업공간 설정
        rg.set_workspace("argilla")
        
        # 데이터셋 목록 가져오기
        datasets = rg.list_datasets()
        print("\n📊 사용 가능한 데이터셋:")
        for i, dataset in enumerate(datasets, 1):
            print(f"  {i}. {dataset}")
        return datasets
    except Exception as e:
        print(f"❌ 데이터셋 목록 가져오기 실패: {e}")
        return []

def export_dataset(dataset_name, output_dir="exported_data"):
    """데이터셋을 JSON과 CSV로 내보내기"""
    try:
        print(f"\n📥 데이터셋 '{dataset_name}' 내보내기 시작...")
        
        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Argilla 데이터셋 로드
        dataset = rg.FeedbackDataset.from_argilla(dataset_name, workspace="argilla")
        
        # 데이터 수집
        all_records = []
        for record in dataset.records:
            record_data = {
                "id": record.id,
                "fields": {},
                "responses": [],
                "suggestions": []
            }
            
            # 필드 데이터 수집
            for field in dataset.fields:
                if hasattr(record.fields, field.name):
                    record_data["fields"][field.name] = getattr(record.fields, field.name)
            
            # 응답 데이터 수집
            if record.responses:
                for response in record.responses:
                    response_data = {
                        "user": response.user_id,
                        "values": {}
                    }
                    for question in dataset.questions:
                        if hasattr(response.values, question.name):
                            value = getattr(response.values, question.name)
                            response_data["values"][question.name] = value.value if hasattr(value, 'value') else value
                    record_data["responses"].append(response_data)
            
            # 제안 데이터 수집
            if record.suggestions:
                for suggestion in record.suggestions:
                    suggestion_data = {
                        "question": suggestion.question_name,
                        "value": suggestion.value
                    }
                    record_data["suggestions"].append(suggestion_data)
            
            all_records.append(record_data)
        
        # JSON으로 저장
        json_file = os.path.join(output_dir, f"{dataset_name}_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "dataset_name": dataset_name,
                "export_date": timestamp,
                "total_records": len(all_records),
                "records": all_records
            }, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 파일 저장됨: {json_file}")
        
        # CSV로 저장 (플랫 구조로 변환)
        csv_data = []
        for record in all_records:
            base_row = {"record_id": record["id"]}
            
            # 필드 추가
            for field_name, field_value in record["fields"].items():
                base_row[f"field_{field_name}"] = field_value
            
            # 응답이 있으면 각 응답별로 행 생성
            if record["responses"]:
                for response in record["responses"]:
                    row = base_row.copy()
                    row["response_user"] = response["user"]
                    for q_name, q_value in response["values"].items():
                        row[f"response_{q_name}"] = q_value
                    csv_data.append(row)
            else:
                # 응답이 없으면 기본 행만 추가
                csv_data.append(base_row)
        
        if csv_data:
            df = pd.DataFrame(csv_data)
            csv_file = os.path.join(output_dir, f"{dataset_name}_{timestamp}.csv")
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"✅ CSV 파일 저장됨: {csv_file}")
        
        # 통계 출력
        print(f"\n📊 내보내기 완료:")
        print(f"  - 총 레코드 수: {len(all_records)}")
        print(f"  - 응답이 있는 레코드: {sum(1 for r in all_records if r['responses'])}")
        print(f"  - 제안이 있는 레코드: {sum(1 for r in all_records if r['suggestions'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터셋 내보내기 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def export_all_datasets(output_dir="exported_data"):
    """모든 데이터셋 내보내기"""
    datasets = list_datasets()
    if not datasets:
        print("내보낼 데이터셋이 없습니다.")
        return
    
    print(f"\n🔄 총 {len(datasets)}개의 데이터셋을 내보냅니다...")
    for dataset_name in datasets:
        export_dataset(dataset_name, output_dir)
        print("-" * 50)

def main():
    """메인 함수"""
    print("=" * 60)
    print("🚀 Argilla 데이터 내보내기 도구")
    print("=" * 60)
    
    # Argilla 서버 연결
    if not connect_to_argilla():
        return
    
    # 데이터셋 목록 표시
    datasets = list_datasets()
    if not datasets:
        print("데이터셋이 없습니다.")
        return
    
    # 사용자 선택
    print("\n선택하세요:")
    print("1. 특정 데이터셋 내보내기")
    print("2. 모든 데이터셋 내보내기")
    print("0. 종료")
    
    choice = input("\n선택 (0-2): ").strip()
    
    if choice == "1":
        dataset_name = input("데이터셋 이름을 입력하세요: ").strip()
        if dataset_name in datasets:
            export_dataset(dataset_name)
        else:
            print(f"❌ 데이터셋 '{dataset_name}'을 찾을 수 없습니다.")
    elif choice == "2":
        export_all_datasets()
    elif choice == "0":
        print("프로그램을 종료합니다.")
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()