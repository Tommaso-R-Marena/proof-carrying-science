clear all;
close all;
clc;

cur_dir = strrep(which('hysteresis_opt'),'hysteresis_opt.m','');
eval(['cd ' cur_dir]);

%% Data generation
theta_opt = 0.5;
[t,d] = ode15s(@(t,x) hysteresisODE(t,[theta_opt,x]),[0,30],4);
d_opt = d(end);
D=d_opt;

%% Options
% options system
opt_VM.simulation = @hysteresisODE;

% options optimization
options_MS.n_starts = 100; % number of multistarts, 100 in manuscript

options_MS.op = odeset('Events',@event,'abstol',1e-6,'reltol',1e-3);%,
options_MS.R_max = 10^12;
options_MS.maxSteps = 5000;

options_MS.gradientDescent = true;

% options VMOF
options_VMOF.retraction_factor = 'const';
lambda_try = [20];

%% Parameters
z0 = [theta_opt-0.1;d_opt];

parameters.guess = z0;
parameters.min = [-2;-3];
parameters.max = [2;6];
parameters.number = 2;

parameters.name = ['theta' 'x'];

z0 = sampleParameters(parameters,options_MS);

%% Initialisation
%% Gradient descent
if options_MS.gradientDescent
    options_VMOF.method = 'gradient-descent';
    for j=1:length(lambda_try)
        options_VMOF.lambda = lambda_try(j);
        opt_VM.lambda = lambda_try(j);
        parameters_EM = Manifold_opt(parameters, @(r,z) VFMO_mod(r,z,@(r,z) ...
            systemHysteresis(r,z,...
            opt_VM.simulation,D),options_VMOF),options_MS);
        parameters.start = parameters_EM.MS.par0;
    end
end

%% Hybrid
global HISTORYs
    HISTORYs.x = [];
    HISTORYs.fval = [];

    optionsS = optimset('fmincon');
    optionsS = optimset(optionsS,'outputfcn',@outfuns);
    optionsS = optimset(optionsS,'GradObj','on');
    optionsS = optimset(optionsS,'algorithm','interior-point','Display','off','TolFun',1e-6,'TolCon',1e-6);
    
%z0 = parameters.start;
opt_system.xTol = 1e-7;
opt_system.convTol = 1e-9;
z0 = parameters.start;
parameters.number = 1;
parameters_FMs = parameters;
parameters_FMs.MS.par_evol = cell(1,options_MS.n_starts);
parameters_FMs.MS.par = nan(size(z0,1),options_MS.n_starts); % saves also x_0_old not only theta sigma
parameters_FMs.MS.gradient = nan(parameters.number,options_MS.n_starts);
parameters_FMs.MS.par0 = z0;
parameters_FMs.MS.n_iter = nan(options_MS.n_starts,1);
parameters_FMs.MS.t_cpu = nan(options_MS.n_starts,1);
parameters_FMs.MS.stopCrit = nan(options_MS.n_starts,2);
parameters_FMs.MS.errorCount = nan(options_MS.n_starts,1);
parameters_FMs.MS.logPost = nan(options_MS.n_starts,1);
parameters_FMs.MS.logPost0 = nan(options_MS.n_starts,1);
parameters_FMs.MS.hessian = nan(parameters.number,parameters.number,options_MS.n_starts); %To Do
parameters_FMs.MS.n_objfun = nan(options_MS.n_starts,1); % To Do

for i =1:options_MS.n_starts
try
    x_0_old = z0(2,i);
    theta_old = z0(1,i);
    J_old = 1e+3;
    x_0_evol = [];
    theta_evol = [];
    save('current_state','theta_old','x_0_old','J_old','x_0_evol','theta_evol')
    T_cpu = cputime;
    [X_fmc, Jval, EF, OP] = fmincon(@(z)J_fmincon_hysteresis_hybrid...
        (z,opt_VM.simulation,...
        D,opt_system),...
        z0(1,i),[],[],[],[],-15*ones(1,1),15*ones(1,1),[],optionsS);
    parameters_FMs.MS.t_cpu(i)= cputime - T_cpu;
    parameters_FMs.MS.par_evol{i} = reshape(HISTORYs.x,1,[]);
    load('current_state')
    Y_FMs_opt(i,:) = x_0_old;
    J_FMs_evol{i} = HISTORYs.fval;
    J_FMs_opt(i) = J_FMs_evol{i}(end);
    parameters_FMs.MS.par(1:1,i) = X_fmc;
    parameters_FMs.MS.par(1+1:end,i) = x_0_old;
    parameters_FMs.MS.logPost(i) = -J_FMs_opt(i);
    parameters_FMs.MS.evol{i} = [theta_evol;x_0_evol];
    output_FMs{i} = OP;
    HISTORYs.x = [];
    HISTORYs.fval = [];
    disp(['start ' num2str(i) '/' num2str(options_MS.n_starts) ])
catch ME
    disp(['start ' num2str(i) '/' num2str(options_MS.n_starts) ' optimization failed'])
    ME.message
end
end

eval(['cd ' cur_dir]);
pathname = 'MS100_hysteresis';
save(pathname,'parameters_FMs','parameters_EM','theta_opt','d_opt')