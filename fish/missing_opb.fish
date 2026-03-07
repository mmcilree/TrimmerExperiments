#!/users/grad/mmcilree/.local/bin/fish
for file in /cluster/roundingsat_proofs_to_trim/*.pbp
    set dir $(dirname $file)
    set name $(basename $file ".pbp")
    if not test -f $dir/$name.opb
        echo $dir/$name.pbp
    end
end