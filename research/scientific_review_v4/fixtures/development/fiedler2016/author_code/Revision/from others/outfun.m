% f_fmincon_DoseResp.m collects the parameter-state vectors along the
% solver path of fmincon

function stop = outfun(x,optimValues,state)
% Store the iteration points xk with respective objective function fk
global HISTORY
stop = false;
switch state
    case 'iter'
       HISTORY.x = [HISTORY.x; x];
       HISTORY.fval = [HISTORY.fval; optimValues.fval];   
    case 'done'
       HISTORY.x = [HISTORY.x; x];
       HISTORY.fval = [HISTORY.fval; optimValues.fval];  
    otherwise
end        