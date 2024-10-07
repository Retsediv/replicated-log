# Replicated Log (Part 1)

## TODOs

- [  ] Add number of clients to env file

## How to run the code


```bash
# build
docker compose build


# run (change .env file with the number of clients you want to run)
source .env
for i in $(seq 1 $NUM_CLIENTS); do CLIENT_INDEX=$i docker compose up --scale client=$i --no-recreate -d; done

# get hostnames
for i in $(docker ps --format  '{{ .Names }}'); do
echo -n "$i: "; docker inspect --type container $i | jq -r '.[].Config.Hostname'
done
```

Development mode:

```bash
docker compose up --watch
```


<!-- (does not support indexing) -->
<!---->
<!-- ```bash -->
<!-- docker-compose up -->
<!-- ``` -->
<!---->
<!-- or you can specify the number of clients to run: -->
<!---->
<!-- ```bash -->
<!-- docker-compose up --scale client=5 -->
<!-- ``` -->
<!---->

