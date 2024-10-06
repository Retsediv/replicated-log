# Replicated Log (Part 1)

## How to run the code

```bash
# build
docker compose build

# run (change 5 to the number of clients you want to run)
for i in $(seq 1 5); do CLIENT_INDEX=$i docker compose up --scale client=$i --no-recreate -d; done

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

