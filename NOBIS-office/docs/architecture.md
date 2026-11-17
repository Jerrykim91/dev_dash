# 현재 아키텍처 — Hybrid World

현재 기준은 [Hybrid World 설계](hybrid-world.md)와 [검증 기록](hybrid-verification.md)입니다. 이전 단일 맵 문서는 [이전 기록](history/before-hybrid-architecture.md)으로 보존합니다.

React UI / Phaser 현재 룸 하나 / FastAPI RoomManager / 기존 인증·경제·소셜 서비스 / SQLite 또는 PostgreSQL입니다. room_instance_id로 위치와 룸 채팅을 격리하며 개인 집은 기존 서비스를 재사용합니다.
