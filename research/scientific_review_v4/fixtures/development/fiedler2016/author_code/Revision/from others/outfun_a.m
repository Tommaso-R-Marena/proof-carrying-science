% f_fmincon_DoseResp.m collects the parameter-state vectors along the
% solver path of fmincon

function stop = outfun_a(x,optimValues,state)
% Store the iteration points xk with respective objective function fk
global HISTORYa
stop = false;
switch state
    case 'iter'
       HISTORYa.x = [HISTORYa.x; x];
       HISTORYa.fval = [HISTORYa.fval; optimValues.fval];   
    case 'done'
       HISTORYa.x = [HISTORYa.x; x];
       HISTORYa.fval = [HISTORYa.fval; optimValues.fval];  
    otherwise
end        