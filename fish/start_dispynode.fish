#!/users/grad/mmcilree/.local/bin/fish
echo "Checking venv"
if [ "$VIRTUAL_ENV" = "" ];
    echo "venv not active, starting venv"
    source /cluster/arthur/roundingsat/venv/bin/activate.fish
end

echo "Getting host"
if not set -q argv[1] ;
    set host $(hostname -I | awk '{print $1}')
else 
    set host $argv[1]
end

systemd-run --scope \
 -p MemoryMax=1000G \
 -p MemorySwapMax=0 \
 --user \
 dispynode.py \
 --cpus 80 \
 -p 11223 \
 -s "dispy_secret_gumbo" \
 -i $host \
 -d