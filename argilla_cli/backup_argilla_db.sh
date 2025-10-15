#!/bin/bash

# Argilla 데이터베이스 백업 스크립트
# PostgreSQL 데이터베이스를 SQL 덤프 파일로 내보냅니다.

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="../argilla_backups"
CONTAINER_NAME="argilla-korean-postgres-1"

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

echo "🔄 Argilla PostgreSQL 데이터베이스 백업 시작..."

# PostgreSQL 덤프 생성
DUMP_FILE="$BACKUP_DIR/argilla_backup_${TIMESTAMP}.sql"
docker exec "$CONTAINER_NAME" pg_dump -U postgres -d argilla > "$DUMP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ 데이터베이스 백업 완료: $DUMP_FILE"
    
    # 압축
    gzip "$DUMP_FILE"
    echo "✅ 압축 완료: ${DUMP_FILE}.gz"
    
    # 파일 크기 확인
    SIZE=$(du -h "${DUMP_FILE}.gz" | cut -f1)
    echo "📦 백업 파일 크기: $SIZE"
else
    echo "❌ 데이터베이스 백업 실패"
    exit 1
fi

echo ""
echo "📌 백업 파일을 복원하려면:"
echo "   1. 압축 해제: gunzip ${DUMP_FILE}.gz"
echo "   2. 복원: docker exec -i $CONTAINER_NAME psql -U postgres -d argilla < $DUMP_FILE"