% ConversionReactionTimeSeries_opt.m compares simulation-based optimization for
% different retraction factors lambda and hybrid optimization on the example of 
% time series data from a simple conversion reaction.

clear all;
close all;
clc;

cur_dir = strrep(which('ConversionReactionTimeSeries_opt'),'ConversionReactionTimeSeries_opt.m','');
eval(['cd ' cur_dir]);

%% Initialization

% parameter and state dimension
n_theta = 2;
n_x = 1;

% measurement time
t_m = [0, 0.1, 0.5, 1, 2]; 

us = 1;
u = 0.4;

% true initial steady state for u0
xs_real = 0.2;
theta_real = [4,1];
ic = [0,0,1]';

% measurements
[~,x_sens] = ode15s(@(t,x)ConversionReactionSens_u(t,[theta_real';x],u),t_m,[xs_real;ic]);
x_opt = x_sens(:,1)';

% data vector
D.measurement{1} = x_opt';
D.t{1} = t_m;
D.conditions = u;
D.u_s = us;

% analytical steady state
x_s = @(theta,u) theta(2,:)./(theta(1,:)*u + theta(2,:));
theta_1_opt = @(theta_2) (theta_2*(1-xs_real))/us*xs_real;

% initial parameter and state for the optimization
theta0 = [2.2;1.5];
x_0 = 0.5;
z0 = [theta0;x_0];

% Integrator setting
op = odeset('abstol',1e-6,'reltol',1e-3,'Events',@event);

% parameter settings
parameters.guess = z0;
parameters.min = [zeros(n_theta,1);zeros(n_x,1)];
parameters.max = [3*ones(n_theta,1);1*ones(n_x,1)];
parameters.number = n_theta+n_x;

% system options
opt_system.n_theta = n_theta;
opt_system.n_x = n_x;

% Manifold_opt options
options_MS.n_starts = 1; % number of starts
options_MS.op = op; %odeset('abstol',1e-6,'reltol',1e-3,'Stats','on');
options_MS.R_max = 10^6; % maximal simulation time for simulation based optimization

% VMOF options
options_VMOF.method = 'gradient-descent';% 'newton-method'; %
options_VMOF.retraction_factor = 'const';

% vector of retraction factor values
lambda_try = [0,1,10];

%% simulation-based optimization - gradient-descent
for j=1:length(lambda_try)
    options_VMOF.lambda = lambda_try(j);
    opt_VM.lambda = lambda_try(j);
    
    % simulation using Manifold_opt, VFMO_mod and a problem specific
    % systems file
    parameters_GD = Manifold_opt(parameters,...
        @(r,z) VFMO_mod(r,z,@(r,z)system_timeseriesDataCR(...
        r,z,@J_normalCR,@ConversionReactionSens_u,@ConversionReaction_u,D,opt_system),options_VMOF),options_MS);
    parameters.start = parameters_GD.MS.par0;
    % Evalutation
    for i = 1:options_MS.n_starts
        try
        Theta_MS{j,i} = parameters_GD.MS.par_evol{i}(:,1:n_theta);
        X0_MS{j,i} = parameters_GD.MS.par_evol{i}(:,(n_theta+1):end);
        compt_MS(j,:) = parameters_GD.MS.t_cpu;
        xs_theta_MS{j,i} = x_s([Theta_MS{j,i}(:,1)';Theta_MS{j,i}(:,2)']);
        catch
        end
    end
    parameters_SD{j} = parameters_GD;
    clear parameters_GD
end

funeval = cellfun(@(x) length(x),X0_MS);

%% Optimisation on manifold

global HISTORYs
    HISTORYs.x = [];
    HISTORYs.fval = [];

    optionsS = optimset('fmincon');
    optionsS = optimset(optionsS,'outputfcn',@outfuns);
    optionsS = optimset(optionsS,'GradObj','on');
    optionsS = optimset(optionsS,'algorithm','interior-point','Display','off','TolFun',1e-6,'TolCon',1e-6);

%% Multistart fmincon
%z0 = parameters.start;
opt_system.xTol = 1e-7;
opt_system.convTol = 1e-9;
z0 = parameters.start;
parameters.number = n_theta;
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
    x_0_old = z0(n_theta+1:end,i);
    theta_old = z0(1:n_theta,i);
    J_old = 1e+3;
    x_0_evol = [];
    theta_evol = [];
    save('current_state','theta_old','x_0_old','J_old','x_0_evol','theta_evol')
    T_cpu = cputime;
    [X_fmc, Jval, EF, OP] = fmincon(@(z)J_fmincon_conversionReaction_u_hybrid...
        (z,@J_normalCR,@ConversionReaction_u,...
        @ConversionReactionSens_u,D,opt_system),...
        z0(1:n_theta,i),[],[],[],[],-15*ones(n_theta,1),15*ones(n_theta,1),[],optionsS);
    parameters_FMs.MS.t_cpu(i)= cputime - T_cpu;
    parameters_FMs.MS.par_evol{i} = reshape(HISTORYs.x,n_theta,[]);
    load('current_state')
    Y_FMs_opt(i,:) = x_0_old;
    J_FMs_evol{i} = HISTORYs.fval;
    J_FMs_opt(i) = J_FMs_evol{i}(end);
    parameters_FMs.MS.par(1:n_theta,i) = X_fmc;
    parameters_FMs.MS.par(n_theta+1:end,i) = x_0_old;
    parameters_FMs.MS.logPost(i) = -J_FMs_opt(i);
    parameters_FMs.MS.evol{i} = [theta_evol;x_0_evol];
    output_FMs{i} = OP;
    HISTORY.x = [];
    HISTORY.fval = [];
    disp(['start ' num2str(i) '/' num2str(options_MS.n_starts) ])
catch ME
    disp(['start ' num2str(i) '/' num2str(options_MS.n_starts) ' optimization failed'])
    ME.message
end
end

save('./Results/optimizationResults')
%% analytical steady state manifold

% % computation for the analytical steady state manifold
% theta_2_grid = linspace(0,1.8,1000)';
% theta_1_grid = linspace(1,8,1000)';
% 
% [Theta_1,Theta_2] = meshgrid(theta_1_grid,theta_2_grid);
% 
% Xs = nan(size(Theta_1));
% for i1 = 1:size(Xs,1)
%     for i2 = 1:size(Xs,2)
%         % analytical steady state at (theta_1,theta_2)
%         Xs(i1,i2) = x_s([Theta_1(i1,i2);Theta_2(i1,i2)],us);
%         % objective function value at (theta_1,theta_2)
%         [~,x_theta] = ode15s(@(t,x)ConversionReactionSens_u(t,[[Theta_1(i1,i2);Theta_2(i1,i2)];x],u),t_m,[Xs(i1,i2);ic]);
%         Js(i1,i2) = J_normalCR(D.measurement{1}(:),x_theta(:,1),ones(length(t_m),n_theta));
%     end
% end
%
% save('./Results/ResultConversionReaction_new')
