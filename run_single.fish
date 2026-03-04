#!/users/grad/mmcilree/.local/bin/fish
set solver_binary $argv[1] 
set instance $argv[2]
set instance_name $(basename $instance ".opb")
set instance_dir $(dirname $instance)
set proof_path /cluster/roundingsat_proofs_to_trim 

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
set solve_cmd $solver_binary $file $instance --proof-log=$proof_path/$instance_name.pbp 2>&1 
set solve_output $($solve_cmd)
set solver_status $status

# Check status
if test $solver_status -ne 0
    echo "Non-zero exit status" 
    rm $proof_path
    echo $solve_cmd
    echo $roundingsat_out
    exit $solver_status
else
    # echo "Success"
    cp $instance $proof_path/$instance_name.opb
end;