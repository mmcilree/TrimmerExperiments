#!/users/grad/mmcilree/.local/bin/fish
set path $argv[1]
set inst_path $argv[2]
set ext $argv[3]
for file in $path/*.pbp; 
    tail $file | grep -q conclusion; 
    and echo $(basename $file ".pbp") $inst_path/$(basename $file ".pbp").$ext $path/$(basename $file ".pbp").pbp; 
end 