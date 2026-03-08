#!/users/grad/mmcilree/.local/bin/fish
set solver_binary $argv[1] 
set instance $argv[2]
set instance_name $(basename $instance ".cnf")
set instance_dir $(dirname $instance)
set proof_path /scratch/kissat_2024_proofs_to_trim

if not test -d $proof_path 
    mkdir $proof_path
end

function remove_proof_files
    echo "Removing proof files">&2
    rm -f $proof_path/$instance_name.pbp
end

function on_sigterm
    remove_proof_files
    exit 143
end

function on_sigint
    remove_proof_files
    exit 130
end

trap on_sigterm TERM
trap on_sigint INT

# Solve
set solve_cmd $solver_binary $instance $instance_name-temp.cnf $proof_path/$instance_name.pbp 2>&1 
set solve_output $($solve_cmd)
set solver_status $status

# Check status
if test $solver_status -eq 20
    cp $instance $proof_path/$instance_name.cnf
    echo $solve_cmd
    echo $solve_output
    exit $solver_status
else echo "Non-exit status" 
    # rm $proof_path/$instance_name.pbp
    echo $solve_cmd
    echo $solve_output
    exit $solver_status
end;