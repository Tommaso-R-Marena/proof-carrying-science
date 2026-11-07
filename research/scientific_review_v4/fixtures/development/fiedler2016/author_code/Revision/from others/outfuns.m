function stop = outfuns(x,optimValues,state)
% Store the iteration points xk with respective objective function fk
global HISTORYs
stop = false;
switch state
    case 'iter'
       HISTORYs.x = [HISTORYs.x; x];
       HISTORYs.fval = [HISTORYs.fval; optimValues.fval];   
    case 'done'
       HISTORYs.x = [HISTORYs.x; x];
       HISTORYs.fval = [HISTORYs.fval; optimValues.fval];  
    otherwise
end        