#!/users/grad/mmcilree/.local/bin/fish
set path $argv[1]
set ext $argv[2]
for file in $path/*.pbp; 
    tail $file | grep -q conclusion; 
    and echo $(basename $file ".pbp") $path/$(basename $file ".pbp").$ext $path/$(basename $file ".pbp").pbp; 
end 