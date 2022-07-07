docker-compose -f web-docker-compose.yml down
docker-compose -f processor-docker-compose.yml down
docker-compose -f web-docker-compose.yml down
docker-compose -f web-docker-compose.yml up -d
docker-compose -f processor-docker-compose.yml up -d
docker container list
_id=`docker container ls  | grep 'processor' | awk '{print $1}'`
docker logs -f $_id
