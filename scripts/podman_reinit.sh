#!/usr/bin/env bash

set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
podman_bin=${PODMAN_BIN:-podman}

network_name="campusnow-net"
mongo_name="campusnow-mongo"
api_name="campusnow-api"
scraper_name="campusnow-scraper"
g2_seeder_name="campusnow-g2-seeder"
mock_seeder_name="campusnow-mock-seeder"

mongo_image="docker.io/library/mongo:7.0"
api_image="localhost/campusnow-api:latest"
scraper_image="localhost/campusnow-scraper:latest"

mongo_uri="mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow?authSource=admin"

log() {
	printf '[podman-reinit] %s\n' "$*"
}

run_ignore_fail() {
	if "$@" >/dev/null 2>&1; then
		return 0
	fi
}

stop_existing_services() {
	if command -v systemctl >/dev/null 2>&1; then
		run_ignore_fail systemctl --user stop mock-seeder.service scraper.service api.service mongodb.service
	fi
}

remove_containers() {
	local containers=(
		"$mock_seeder_name"
		"$g2_seeder_name"
		"$scraper_name"
		"$api_name"
		"$mongo_name"
	)

	for container in "${containers[@]}"; do
		run_ignore_fail "$podman_bin" rm -f -t 10 "$container"
	done
}

remove_project_volumes() {
	mapfile -t project_volumes < <(
		"$podman_bin" volume ls --format '{{.Name}}' |
			grep -E '^(campusnow|mongo_data)([._-]|$)' || true
	)

	if ((${#project_volumes[@]} > 0)); then
		run_ignore_fail "$podman_bin" volume rm -f "${project_volumes[@]}"
	fi
}

clear_bind_mounts() {
	local data_dirs=(
		"$repo_root/data/db"
		"$repo_root/data/images/360"
	)

	for data_dir in "${data_dirs[@]}"; do
		mkdir -p "$data_dir"
		"$podman_bin" unshare bash -c 'find "$1" -mindepth 1 -maxdepth 1 -exec rm -rf {} +' _ "$data_dir" >/dev/null 2>&1 || true
	done
}

remove_images() {
	run_ignore_fail "$podman_bin" rmi -f "$api_image" "$scraper_image" "$mongo_image"
}

build_images() {
	log "Building API image"
	"$podman_bin" build --pull=always --no-cache -t "$api_image" -f "$repo_root/backend/api-service/Dockerfile" "$repo_root/backend/api-service"

	log "Building scraper image"
	"$podman_bin" build --pull=always --no-cache -t "$scraper_image" -f "$repo_root/backend/scraper-service/Dockerfile" "$repo_root/backend/scraper-service"
}

ensure_network() {
	if ! "$podman_bin" network inspect "$network_name" >/dev/null 2>&1; then
		"$podman_bin" network create "$network_name" >/dev/null
	fi
}

wait_for_mongo() {
	log "Waiting for MongoDB"
	for _ in $(seq 1 60); do
		if "$podman_bin" exec "$mongo_name" mongosh --quiet --host 127.0.0.1 --port 27017 -u admin -p campusnow_secret_2025 --authenticationDatabase admin --eval 'db.adminCommand({ ping: 1 }).ok' >/dev/null 2>&1; then
			return 0
		fi
		sleep 2
	done

	echo "MongoDB did not become ready in time" >&2
	"$podman_bin" logs "$mongo_name" >&2 || true
	exit 1
}

wait_for_api() {
	if ! command -v curl >/dev/null 2>&1; then
		return 0
	fi

	log "Waiting for API"
	for _ in $(seq 1 60); do
		if curl -fsS http://127.0.0.1:6058/health >/dev/null 2>&1; then
			return 0
		fi
		sleep 2
	done

	echo "API did not become ready in time" >&2
	"$podman_bin" logs "$api_name" >&2 || true
	exit 1
}

start_mongo() {
	log "Starting MongoDB"
	"$podman_bin" run -d \
		--name "$mongo_name" \
		--network "$network_name" \
		--network-alias mongodb \
		-p 27017:27017 \
		-e MONGO_INITDB_ROOT_USERNAME=admin \
		-e MONGO_INITDB_ROOT_PASSWORD=campusnow_secret_2025 \
		-e MONGO_INITDB_DATABASE=campusnow \
		-e TZ=Europe/Berlin \
		-v "$repo_root/data/db:/data/db:Z" \
		-v "$repo_root/scripts/init_db.js:/docker-entrypoint-initdb.d/init.js:Z,ro" \
		"$mongo_image" >/dev/null
}

run_g2_seeder() {
	log "Seeding G2 rooms"
	"$podman_bin" run --rm \
		--name "$g2_seeder_name" \
		--network "$network_name" \
		-e MONGO_URI="$mongo_uri" \
		-e MONGO_DB=campusnow \
		-e TZ=Europe/Berlin \
		-v "$repo_root/backend/api-service:/app:Z" \
		"$api_image" \
		python seed_g2_rooms.py >/dev/null
}

run_mock_seeder() {
	log "Seeding mock data"
	"$podman_bin" run --rm \
		--name "$mock_seeder_name" \
		--network "$network_name" \
		-e MONGO_URI="$mongo_uri" \
		-e MONGO_DB=campusnow \
		-e MOCK_ROOM_ID=MOCK-R1 \
		-e MOCK_BUILDING_ID=AH \
		-e TZ=Europe/Berlin \
		-v "$repo_root/backend/api-service:/app:Z" \
		-v "$repo_root/data/images/360:/app/data/images/360:Z" \
		"$api_image" \
		python seed_mock_data.py >/dev/null
}

start_api() {
	log "Starting API"
	"$podman_bin" run -d \
		--name "$api_name" \
		--network "$network_name" \
		-p 6058:8000 \
		-e MONGO_URI="$mongo_uri" \
		-e MONGO_DB=campusnow \
		-e API_TITLE="CampusNow API" \
		-e API_VERSION=1.0.0 \
		-e CORS_ORIGINS='*' \
		-e LOG_LEVEL=INFO \
		-e TZ=Europe/Berlin \
		-v "$repo_root/backend/api-service:/app:Z" \
		-v "$repo_root/data/images/360:/app/data/images/360:Z" \
		"$api_image" >/dev/null
}

start_scraper() {
	log "Starting scraper"
	"$podman_bin" run -d \
		--name "$scraper_name" \
		--network "$network_name" \
		-e MONGO_URI="$mongo_uri" \
		-e MONGO_DB=campusnow \
		-e LOG_LEVEL=INFO \
		-e TZ=Europe/Berlin \
		-v "$repo_root/backend/scraper-service:/app:Z" \
		-v "$repo_root/data/images/360:/app/data/images/360:Z" \
		"$scraper_image" >/dev/null
}

main() {
	log "Stopping existing CampusNow services"
	stop_existing_services
	remove_containers
	remove_project_volumes
	clear_bind_mounts
	remove_images
	ensure_network
	build_images
	start_mongo
	wait_for_mongo
	run_g2_seeder
	run_mock_seeder
	start_api
	start_scraper
	wait_for_api

	log "Reset complete"
	"$podman_bin" ps --filter "name=campusnow" --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'
}

main "$@"