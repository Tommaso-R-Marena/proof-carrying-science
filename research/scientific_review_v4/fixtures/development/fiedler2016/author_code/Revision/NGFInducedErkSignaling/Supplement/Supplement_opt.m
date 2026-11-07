clear all;
close all;
clc;

cur_dir = strrep(which('Supplement_opt'),'Supplement_opt.m','');
eval(['cd ' cur_dir]);

%% Data
load('../Data/DoseResponsedata.mat')
%% Model
% analytical steady state
x_10 = @(xi,u) 10^xi(1).*u*10^xi(5)./(10^xi(1).*u+10^xi(2));
x_20 = @(x1,xi,u) (10^xi(3)+x1)*10^xi(6)./(10^xi(3)+x1+10^xi(4));

n_theta = 6;
%% Initialization
xi0 =0.16*ones(n_theta,1);

theta0 = 10.^(xi0);

x_s(1,:)= x_10(xi0,D.u);
x_s(2,:)= x_20(x_s(1,:),xi0,D.u);

x0_start = x_s(:);
sigma0 = 0.1^2;
n_sigma = 1;

n_xi = length(xi0);
n_x = 2;%length(x0_start);

%% Options
% options system
opt_VM.n_theta = n_theta;
opt_VM.n_x = n_x;
opt_VM.u = D.u;
opt_VM.objective = @J_normal;
opt_VM.penalty = @J_theta_quadPen;
opt_VM.simulation = @Erk_pathway_A_log;

% options optimization
options_SD.n_starts = 1;

options_SD.op = odeset('Events',@event,'abstol',1e-6,'reltol',1e-3);%,
options_SD.R_max = 10^12;
options_SD.maxSteps = 10000; % more max function evaluations than in application in manuscript 
% options_SD.steadyState = @(theta) x0(exp(theta));

options_SD.gradientDescent = true;
options_SD.newtonMethod =  true;
options_SD.fminconOn = false;
options_SD.fminconHybridOn = false;
options_SD.fminuncOn = false;

% options VMOF
options_VMOF.retraction_factor = 'const';
lambda_try = exp([linspace(log(0.02),log(20),5),linspace(log(20),log(2000),5),log(10000)]);
lambda_try = lambda_try([1:5,7:end]);

%% parameter bounds
D.theta_max = 3.5*ones(n_theta+n_sigma,1);
D.theta_min = [-5*ones(n_theta,1);-5*ones(n_sigma,1)];

D.sigma = 10;
D.delta = 10000;

%% Parameters
z0 = [xi0;sigma0;x0_start(:)];

parameters.guess = z0;
parameters.min = [-5*ones(n_theta+n_sigma,1);zeros(n_x*length(D.u),1)];
parameters.max = [3.5*ones(n_theta+n_sigma,1);3*ones(n_x*length(D.u),1)];
parameters.number = n_theta+n_sigma+n_x*length(D.u);

str_theta = strtrim(cellstr(int2str([1:n_theta].')));
str_theta = strcat({'\theta'},str_theta);

str_sigma =strtrim(cellstr(int2str([1:n_sigma].')));
str_sigma = strcat({'\sigma'},str_sigma);

str_x0 = strtrim(cellstr(int2str([1:n_x].')));
str_x0 = strcat({'x0'},str_x0);
str_x0 = repmat(str_x0,length(D.u),1);

parameters.name = [str_theta;str_sigma;str_x0];

z0 = sampleParameters(parameters,options_SD);

%% Initialisation
%% Gradient descent
if options_SD.gradientDescent
    options_VMOF.method = 'gradient-descent';
    for j=1:length(lambda_try)
        x_SD = zeros(options_SD.n_starts,length(x0_start));
        options_VMOF.lambda = lambda_try(j);
        opt_VM.lambda = lambda_try(j);
        parameters_EM = Manifold_opt(parameters, @(r,z) VFMO_mod(r,z,@(r,z) ...
            system_ErkDoseResp_JNormal(r,z,opt_VM.objective,opt_VM.penalty,...
            opt_VM.simulation,D,opt_VM),options_VMOF),options_SD);
        parameters.start = parameters_EM.MS.par0;
    % Evalutation
        for i = 1:options_SD.n_starts
            try
            Y_ODE_SD_opt(i,:) = parameters_EM.MS.par(n_theta+n_sigma+2:n_x:end,i)';
            x1_SD(i,:) = x_10(parameters_EM.MS.par(1:n_theta,i),D.u);
            x2_SD(i,:) = x_20(squeeze(x1_SD(i,:)),parameters_EM.MS.par(1:n_theta,i),D.u);
            x_SD(i,1:2:end) = x1_SD(i,:);
            x_SD(i,2:2:end) = x2_SD(i,:);
            dist_SS(i) = norm(squeeze(x_SD(i,:))'-parameters_EM.MS.par(n_theta+n_sigma+1:end,i));
            for k = 1:size(parameters_EM.MS.par_evol{i},1)
                x1_SD_evol{j,i}(k,:) = x_10(parameters_EM.MS.par_evol{i}(k,1:n_theta),D.u);
                x2_SD_evol{j,i}(k,:) = x_20(squeeze(x1_SD_evol{j,i}(k,:)),parameters_EM.MS.par_evol{i}(k,1:n_theta),D.u);
            end
            
            catch ME
                 disp([ME.message , 'gradient descent start ', num2str(i)])
            end
        end
        parameters_EM.MS.sigmaInterval = [bsxfun(@minus,permute(Y_ODE_SD_opt,[3,1,2]),...
                2*sqrt(exp(parameters_EM.MS.par(n_theta+n_sigma,:))));...
                bsxfun(@plus,permute(Y_ODE_SD_opt,[3,1,2]),2*sqrt(exp(parameters_EM.MS.par(n_theta+n_sigma,:))))];
        parameters_EM.MS.trueSteadystate = x_SD;
        parameters_EM.MS.distSS = dist_SS;
        parameters_SD{j} = parameters_EM;
        clear parameters_EM
    end
end

%% Newton method
if options_SD.newtonMethod
    options_VMOF.method = 'newton-method';

    for j=1:length(lambda_try)
        x_NM = zeros(options_SD.n_starts,length(x0_start));
        options_VMOF.lambda = lambda_try(j);
        opt_VM.lambda = lambda_try(j);
        parameters_EM = Manifold_opt(parameters, @(r,z) VFMO_mod(r,z,@(r,z) ...
            system_ErkDoseResp_JNormal(r,z,opt_VM.objective,opt_VM.penalty,...
            opt_VM.simulation,D,opt_VM),options_VMOF),options_SD);
        parameters.start = parameters_EM.MS.par0;
    % Evalutation
        for i = 1:options_SD.n_starts
            try
            Y_ODE_NM_opt(i,:) = parameters_EM.MS.par(n_theta+n_sigma+2:n_x:end,i)';
            x1_NM(i,:) = x_10(parameters_EM.MS.par(1:n_theta,i),D.u);
            x2_NM(i,:) = x_20(squeeze(x1_NM(i,:)),parameters_EM.MS.par(1:n_theta,i),D.u);
            x_NM(i,1:2:end) = x1_NM(i,:);
            x_NM(i,2:2:end) = x2_NM(i,:);
            dist_SS(i) = norm(squeeze(x_NM(i,:))'-parameters_EM.MS.par(n_theta+n_sigma+1:end,i));
            for k = 1:size(parameters_EM.MS.par_evol{i},1)
                x1_NM_evol{j,i}(k,:) = x_10(parameters_EM.MS.par_evol{i}(k,1:n_theta),D.u);
                x2_NM_evol{j,i}(k,:) = x_20(squeeze(x1_NM_evol{j,i}(k,:)),parameters_EM.MS.par_evol{i}(k,1:n_theta),D.u);
            end
            
            catch ME
                 disp([ME.message , 'newton-method start ', num2str(i)])
            end
        end
        parameters_EM.MS.sigmaInterval = [bsxfun(@minus,permute(Y_ODE_NM_opt,[3,1,2]),...
                2*sqrt(exp(parameters_EM.MS.par(n_theta+n_sigma,:))));...
                bsxfun(@plus,permute(Y_ODE_NM_opt,[3,1,2]),2*sqrt(exp(parameters_EM.MS.par(n_theta+n_sigma,:))))];
        parameters_EM.MS.trueSteadyState = x_SD;
        parameters_EM.MS.distSS = dist_SS;
        parameters_NM{j} = parameters_EM;
        clear parameters_EM
    end
end

%% Fimcon
if options_SD.fminconOn
    global HISTORY
        HISTORY.x = [];
        HISTORY.fval = [];
        options = optimset('fmincon');
        options = optimset(options,'outputfcn',@outfun);
        options = optimset(options,'GradObj','on','GradConstr','on');
        options = optimset(options,'algorithm','interior-point','Display','off','TolFun',1e-6,'TolCon',1e-6);

    %% Multistart fmincon
    z0 = parameters.start;
    parameters_FM = parameters;
    parameters_FM.MS.par_evol = cell(1,options_SD.n_starts);
    parameters_FM.MS.par = nan(parameters.number,options_SD.n_starts);
    parameters_FM.MS.gradient = nan(parameters.number,options_SD.n_starts);
    parameters_FM.MS.par0 = z0;
    parameters_FM.MS.n_iter = nan(options_SD.n_starts,1);
    parameters_FM.MS.t_cpu = nan(options_SD.n_starts,1);
    parameters_FM.MS.stopCrit = nan(options_SD.n_starts,2);
    parameters_FM.MS.errorCount = nan(options_SD.n_starts,1);
    parameters_FM.MS.logPost = nan(options_SD.n_starts,1);
    parameters_FM.MS.logPost0 = nan(options_SD.n_starts,1);
    parameters_FM.MS.hessian = nan(parameters.number,parameters.number,options_SD.n_starts); %To Do
    parameters_FM.MS.n_objfun = nan(options_SD.n_starts); % To Do
    x_FM = zeros(options_SD.n_starts,length(x0_start));

    for i=1:options_SD.n_starts
        try
            T_cpu = cputime;
            [X_fmc, Jval, EF, OP] = fmincon(@(z)J_fmincon_DoseResp_normal(z,opt_VM.objective,opt_VM.penalty,D,opt_VM),...
                z0(:,i),[],[],[],[],[],[],@(z)f_fmincon_DoseResp(z(n_theta+n_sigma+1:end),z(1:n_theta+n_sigma),D),options);
            parameters_FM.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FM.MS.par_evol{i} = reshape(HISTORY.x,n_x*length(D.u)+n_theta+n_sigma,[]);
            J_FM_evol{i} = HISTORY.fval;
            J_FM_opt(i) = J_FM_evol{i}(end);
            Xi_fmincon_MS{i} = parameters_FM.MS.par_evol{i}(1:n_theta,:)';
            Theta_fmincon_MS{i} = 10.^Xi_fmincon_MS{i};
            X0_fmincon_MS{i} = parameters_FM.MS.par_evol{i}(1+n_theta+n_sigma:end,:)';
            parameters_FM.MS.par(:,i) = X_fmc;
            parameters_FM.MS.logPost(i) = -J_FM_opt(i);
            Y_FM_opt(i,:) = parameters_FM.MS.par(n_theta+n_sigma+2:n_x:end,i)';
            x1_FM(i,:) = x_10(parameters_FM.MS.par(1:n_theta,i),D.u);
            x2_FM(i,:) = x_20(squeeze(x1_FM(i,:)),parameters_FM.MS.par(1:n_theta,i),D.u);
            x_FM(i,1:2:end) = x1_FM(i,:);
            x_FM(i,2:2:end) = x2_FM(i,:);
            parameters_FM.MS.n_iter(i) = OP.iterations;
            parameters_FM.MS.n_objfun(i) = OP.funcCount;
            dist_SSFM(i) = norm(squeeze(x_FM(i,:))'-parameters_FM.MS.par(n_theta+n_sigma+1:end,i));
            for k = 1:size(parameters_FM.MS.par_evol{i},1)
                x1_FM_evol{i}(k,:) = x_10(parameters_FM.MS.par_evol{i}(k,1:n_theta),D.u);
                x2_FM_evol{i}(k,:) = x_20(squeeze(x1_FM_evol{i}(k,:)),parameters_FM.MS.par_evol{i}(k,1:n_theta),D.u);
            end
            HISTORY.x = [];
            HISTORY.fval = [];
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ])
        catch ME
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ' optimization failed'])
            disp(ME.message)
        end

        for k = 1:size(parameters_FM.MS.par_evol{i},2)
            x1_k_FM{i}(k,:) = x_10(parameters_FM.MS.par_evol{i}(1:6,k),D.u);
            x2_k_FM{i}(k,:) = x_20(x1_k_FM{i}(k,:),parameters_FM.MS.par_evol{i}(1:6,k),D.u);
        end

    end
    parameters_FM.MS.sigmaInterval = [bsxfun(@minus,permute(Y_FM_opt,[3 1 2]),...
                2*exp(parameters_FM.MS.par(n_theta+n_sigma,:)));...
                bsxfun(@plus,permute(Y_FM_opt,[3 1 2]),2*exp(parameters_FM.MS.par(n_theta+n_sigma,:)))];
    parameters_FM.MS.distSS = dist_SSFM;
end

%% Fimcon semianalytic
if options_SD.fminconHybridOn
    global HISTORYs
        HISTORYs.x = [];
        HISTORYs.fval = [];
        optionsS = optimset('fminunc');
        optionsS = optimset(optionsS,'outputfcn',@outfuns);
        optionsS = optimset(optionsS,'GradObj','on');
        optionsS = optimset(optionsS,'algorithm','interior-point','Display','off','TolFun',1e-6,'TolCon',1e-6);

    %% Multistart fmincon
    parameters.number = n_theta+n_sigma;
    parameters_FMs = parameters;
    parameters_FMs.MS.par_evol = cell(1,options_SD.n_starts);
    parameters_FMs.MS.par = nan(parameters.number,options_SD.n_starts);
    parameters_FMs.MS.gradient = nan(parameters.number,options_SD.n_starts);
    parameters_FMs.MS.par0 = z0;
    parameters_FMs.MS.n_iter = nan(options_SD.n_starts,1);
    parameters_FMs.MS.t_cpu = nan(options_SD.n_starts,1);
    parameters_FMs.MS.stopCrit = nan(options_SD.n_starts,2);
    parameters_FMs.MS.errorCount = nan(options_SD.n_starts,1);
    parameters_FMs.MS.logPost = nan(options_SD.n_starts,1);
    parameters_FMs.MS.logPost0 = nan(options_SD.n_starts,1);
    parameters_FMs.MS.hessian = nan(parameters.number,parameters.number,options_SD.n_starts); %To Do
    parameters_FMs.MS.n_objfun = nan(options_SD.n_starts); % To Do
 

    for i=1:options_SD.n_starts
        try
            x_0_old = z0(n_theta+n_sigma+1:end,i);
            theta_old = z0(1:n_theta,i);
            J_old = 1e+3;
            save('current_state','theta_old','x_0_old','J_old')
            T_cpu = cputime;
            [X_fmc, Jval, EF, OP] = fminunc(@(z)J_fmincon_DoseResp_normal_semia...
                (z,opt_VM.objective,opt_VM.penalty,opt_VM.simulation,...
                @Erk_pathway_A_log_xdot,D,opt_VM),...
                z0(1:n_theta+n_sigma,i),optionsS);
            parameters_FMs.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FMs.MS.par_evol{i} = reshape(HISTORYs.x,n_theta+n_sigma,[]);
            J_FMs_evol{i} = HISTORYs.fval;
            J_FMs_opt(i) = J_FMs_evol{i}(end);
            parameters_FMs.MS.par(:,i) = X_fmc;
            parameters_FMs.MS.logPost(i) = -J_FMs_opt(i);
            HISTORY.x = [];
            HISTORY.fval = [];
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ])
        catch ME
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ' optimization failed'])
            ME.message
        end
    end
end

%% Fminunc with analytic steady state
if options_SD.fminuncOn
    global HISTORYa
        HISTORYa.x = [];
        HISTORYa.fval = [];
        optionsa = optimset('fminunc');
        optionsa = optimset(optionsa,'outputfcn',@outfun_a);
        optionsa = optimset(optionsa,'GradObj','on');
        optionsa = optimset(optionsa,'algorithm','interior-point','Display','off','TolFun',1e-6,'TolCon',1e-6);

    %% Multistart Fminunc
    xi0 = parameters.start(1:n_theta+n_sigma,:);

    parameters_FUa.number = n_theta+n_sigma;
    parameters_FUa.min = parameters.min(1:n_theta+n_sigma);
    parameters_FUa.max = parameters.max(1:n_theta+n_sigma);
    parameters_FUa.name = parameters.name;
    parameters_FUa.MS.par_evol = cell(1,options_SD.n_starts);
    parameters_FUa.MS.par = nan(n_theta+n_sigma,options_SD.n_starts);
    parameters_FUa.MS.gradient = nan(n_theta+n_sigma,options_SD.n_starts);
    parameters_FUa.MS.par0 = xi0;
    parameters_FUa.MS.n_iter = nan(options_SD.n_starts,1);
    parameters_FUa.MS.t_cpu = nan(options_SD.n_starts,1);
    parameters_FUa.MS.stopCrit = nan(options_SD.n_starts,2);
    parameters_FUa.MS.errorCount = nan(options_SD.n_starts,1);
    parameters_FUa.MS.logPost = nan(options_SD.n_starts,1);
    parameters_FUa.MS.logPost0 = nan(options_SD.n_starts,1);
    parameters_FUa.MS.hessian = nan(parameters.number,parameters.number,options_SD.n_starts); %To Do
    parameters_FUa.MS.n_objfun = nan(options_SD.n_starts); % To Do

    for i=1:options_SD.n_starts
        try
            T_cpu = cputime;
            [X_fmu, Jval, EF, OP] = fminunc(@(z)J_fmincon_a_DoseResp_normal(z,opt_VM.objective,opt_VM.penalty,D,opt_VM),xi0(:,i),optionsa);
            parameters_FUa.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FUa.MS.par_evol{i} = reshape(HISTORYa.x,n_theta+n_sigma,[]);
            Theta_fminunc_a_MS{i} = 10.^parameters_FUa.MS.par_evol{i};
            parameters_FUa.MS.par(:,i) = X_fmu;
            J_FUa_evol{i} = HISTORYa.fval;
            J_FUa_opt(i) = J_FUa_evol{i}(end);
            parameters_FUa.MS.logPost(i) = -J_FUa_opt(i);
            HISTORYa.x = [];
            HISTORYa.fval = [];
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ])
        catch EM
           disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ' optimization failed'])
           EM.message
        end
    end
end
eval(['cd ' cur_dir]);
pathname = 'MS100lambdaMoreSteps_new';
save(pathname)