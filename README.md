# Replicated Log (Part 2)

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

## API

Note: Substitute port with the port of the master/client you want to interact with.

1. Submit a new message to the log

   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"message": "Hello World"}' http://localhost:6000/submit
   # curl --header "Content-Type: application/json"
   #     --request POST \
   #     --data '{"text": "first"}' \
   #     http://localhost:6000/messages
   ```

2. Submit a new message with the write concern

   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"message": "Hello World", "write_concern": 1}' http://localhost:6000/submit
   ```

3. Get the log
   ```bash
   curl localhost:6000/messages
   ```
