#!/users/grad/mmcilree/.local/bin/fish
set path /scratch/ciaran/20260224-trimming
set proof $argv[1]

set found 0
for node in 01 02 03 04 07 08 09;
    set find_res $(ssh -tq fataepyc-$node "test -d $path && find $path -name $proof -type f | xargs -I {} du {}")
    echo $find_res | grep -q $proof; and set found 1; and break
end

if test $found -eq 1;
   echo $find_res | awk '{ print $1 }'
   exit 0
else
    exit 1
end;