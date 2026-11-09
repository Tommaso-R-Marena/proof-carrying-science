clear
close all
clc

cur_dir = strrep(which('modelComparison'),'modelComparison.m','');
eval(['cd ' cur_dir]);

%% model
n_x = 3;
n_theta = 19;
n_sigma = 2;

%% Read data
% % prior
Y = csvread('TetON__w_Dox__w_prior.csv',1,0);

D.t{1} = Y(1:7,1);
D.measurement{1} = Y(1:7,[4,5,8,9,12,13,16,17]);
scale = D.measurement{1}(1,:);
D.measurement{1} = bsxfun(@rdivide,D.measurement{1},scale);

% UO
Y = csvread('TetON__w_Dox__w_30muM_UO.csv',1,0);

D.t{2} = Y(1:7,1);
D.measurement{2} = Y(1:7,[4,5,8,9,12,13,16,17]);
D.measurement{2} = bsxfun(@rdivide,D.measurement{2},scale);

% Sora
Y = csvread('TetON__w_Dox__w_5muM_Sora.csv',1,0);

D.t{3} = Y(1:7,1);
D.measurement{3} = bsxfun(@rdivide,Y(1:7,[4,5,8,9,12,13,16,17]),scale);

sc = exp([0,-0.2,2.3,1.2,1.3,-0.1,-0.3,0.3]);
sigma2 = ([max(max(D.measurement{1}(:,1:2:end))),...
    max(max(D.measurement{1}(:,2:2:end)))].^2).*[0.01,0.02].^2;

% conditions
D.conditions = [zeros(1,2);[0,30];[5,0]];
n_u = size(D.conditions,1);
D.u_s = [0,0];

% boundaries
D.prior = nan(n_theta+n_sigma,1);
D.theta_max = log(1e2)*ones(n_theta+n_sigma,1);
D.theta_min = [log(1e-4)*ones(n_theta,1);log(1e-10)*ones(n_sigma,1)];
D.sigma = 10;
D.delta = 10000;

%% Analysis
n_t = length(D.t{1});

%analytical steady state
% x0 = @(theta) [((theta(7)*(theta(8)) + (theta(7)^2*(theta(8))^2 + (2*theta(7)^2*theta(5)*(theta(8))^2)/theta(6) + (theta(7)^2*theta(5)^2*(theta(8))^2)/theta(6)^2 + (theta(7)^2*theta(3)^2*theta(5)^2*(theta(8) + theta(1)/theta(2))^2)/(theta(4)^2*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)^2*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)) + (4*theta(7)*theta(1)*theta(3)*theta(5)*(theta(8)))/(theta(2)*theta(4)*theta(6)))^(1/2) + (theta(7)*theta(5)*(theta(8)))/theta(6) - (theta(7)*theta(3)*theta(5)*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6))))/(2*(theta(1)/theta(2)  + theta(7)*theta(8) + (theta(7)*theta(1))/theta(2) + (theta(7)*theta(1)*theta(5))/(theta(2)*theta(6)) + (theta(7)*theta(5)*theta(8))/theta(6))) ...
%  (((theta(7)^2*(theta(8))^2 + (2*theta(7)^2*theta(5)*(theta(8))^2)/theta(6) + (theta(7)^2*theta(5)^2*(theta(8))^2)/theta(6)^2 + (theta(7)^2*theta(3)^2*theta(5)^2*(theta(8) + theta(1)/theta(2))^2)/(theta(4)^2*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)^2*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)) + (4*theta(7)*theta(1)*theta(3)*theta(5)*(theta(8)))/(theta(2)*theta(4)*theta(6)))^(1/2) + theta(7)*theta(8) + (theta(7)*theta(5)*theta(8))/theta(6) - (theta(7)*theta(1)*theta(3)*theta(5))/(theta(2)*theta(4)*theta(6)) - (theta(7)*theta(3)*theta(5)*theta(8))/(theta(4)*theta(6))))/((theta(7)^2*(theta(8))^2 + (2*theta(7)^2*theta(5)*(theta(8))^2)/theta(6) + (theta(7)^2*theta(5)^2*(theta(8))^2)/theta(6)^2 + (theta(7)^2*theta(3)^2*theta(5)^2*(theta(8) + theta(1)/theta(2))^2)/(theta(4)^2*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)^2*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)) + (4*theta(7)*theta(1)*theta(3)*theta(5)*(theta(8)))/(theta(2)*theta(4)*theta(6)))^(1/2) + theta(7)*theta(8) + (theta(7)*theta(5)*(theta(8)))/theta(6) + (theta(1)*theta(3)*(2*theta(7) + (theta(7)*theta(5))/theta(6) + 2))/(theta(2)*theta(4)) + (theta(7)*theta(3)*(theta(8))*(theta(5)/theta(6) + 2))/theta(4)) ...
%  (((theta(7)^2*(theta(8))^2 + (2*theta(7)^2*theta(5)*(theta(8))^2)/theta(6) + (theta(7)^2*theta(5)^2*(theta(8))^2)/theta(6)^2 + (theta(7)^2*theta(3)^2*theta(5)^2*(theta(8) + theta(1)/theta(2))^2)/(theta(4)^2*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)^2*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)) + (4*theta(7)*theta(1)*theta(3)*theta(5)*(theta(8)))/(theta(2)*theta(4)*theta(6)))^(1/2) + theta(7)*theta(8) + (theta(7)*theta(5)*theta(8))/theta(6) - (theta(7)*theta(1)*theta(3)*theta(5))/(theta(2)*theta(4)*theta(6)) - (theta(7)*theta(3)*theta(5)*theta(8))/(theta(4)*theta(6))))/((theta(5)/theta(6) + 1)*(theta(7)^2*(theta(8))^2 + (2*theta(7)^2*theta(5)*(theta(8))^2)/theta(6) + (theta(7)^2*theta(5)^2*(theta(8))^2)/theta(6)^2 + (theta(7)^2*theta(3)^2*theta(5)^2*(theta(8) + theta(1)/theta(2))^2)/(theta(4)^2*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)^2*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)^2) + (2*theta(7)^2*theta(3)*theta(5)*(theta(8))*(theta(8) + theta(1)/theta(2)))/(theta(4)*theta(6)) + (4*theta(7)*theta(1)*theta(3)*theta(5)*(theta(8)))/(theta(2)*theta(4)*theta(6)))^(1/2) + theta(7)*theta(8)*(theta(5)/theta(6) + 1)^2 + (theta(1)*theta(3)*theta(5)*(theta(7) + (theta(7)*theta(5))/theta(6) + 2))/(theta(2)*theta(4)*theta(6)) + (theta(7)*theta(3)*theta(5)*(theta(8))*(theta(5)/theta(6) + 1))/(theta(4)*theta(6)))];

x0 =@(theta) [(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1)) ...
            theta(4)*(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1))/(theta(4)*(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1))+theta(3)) ...
            theta(6)*(theta(4)*(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1))/(theta(4)*(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1))+theta(3)))/(theta(6)*(theta(4)*(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1)))/(theta(4)*(theta(2)*theta(7))/(theta(2)*theta(7)+theta(1))+theta(3))+theta(5))];
%% Options
% options system
opt_VM.n_theta = n_theta;
opt_VM.n_x = n_x;
opt_VM.objective = @J_normal;
opt_VM.penalty = @J_theta_quadPen;
opt_VM.prior = @J_theta_normalPrior;
opt_VM.simulation = @simulate_RafMekErklin_woFeedback; % model without feedback
opt_VM.jacobian = @RafMekErklin_woFeedbacklog_Jac; % model without feedback

% options optimization
options_SD.n_starts = 1;% number of multistarts, 1000 in manuscript

options_SD.op = odeset('abstol',1e-6,'reltol',1e-3,'Events',@event);
options_SD.R_max = 10^25;
options_SD.maxSteps = 22000;

%options_SD.steadyState = @(theta) x0(exp(theta));

options_SD.gradientDescent = false;
options_SD.newtonMethod = false;
options_SD.fminconOn = false;
options_SD.fminconSemiaOn = false;
options_SD.fminuncOn = true;

% options VMOF
options_VMOF.retraction_factor = 'const';
lambda_try = 10^9;

%% Parameters
theta_sigma = [0.0175,3,0.1473,0.5131,0.7947,-1.1956,-3.5649,-1.1914,...
    -0.0818,-0.5822,-0.7343,log(sc),log(sigma2)]+0.1;

parameters.guess = [theta_sigma,x0(exp(theta_sigma))]';%z0;
parameters.min = [log(1e-4)*ones(n_theta,1);log(1e-10)*ones(n_sigma,1);zeros(n_x,1)+1e-7];
parameters.max = [log(1e2)*ones(n_theta,1);log(1e2)*ones(n_sigma,1);1*ones(n_x,1)];
parameters.number = n_theta+n_x+n_sigma;

str_theta = strtrim(cellstr(int2str([1:n_theta].')));
str_theta = strcat({'\theta'},str_theta);

str_sigma =strtrim(cellstr(int2str([1:n_sigma].')));
str_sigma = strcat({'\sigma'},str_sigma);

str_x0 = strtrim(cellstr(int2str([1:n_x].')));
str_x0 = strcat({'x0'},str_x0);
%str_x0 = repmat(str_x0,length(D.u),1);

parameters.name = [str_theta;str_sigma;str_x0];

%% sample parameters

z0 = sampleParameters(parameters,options_SD);
%% gradient descent
if options_SD.gradientDescent
    options_VMOF.method = 'gradient-descent';
    
    for j=1:length(lambda_try)
        options_VMOF.lambda = lambda_try(j);
        opt_VM.lambda = lambda_try(j);
        parameters = Manifold_opt(parameters, @(r,z) VFMO_mod(r,z,@(r,z)system_timeseriesData_JNormal_lin_v2(r,z,opt_VM.objective, ...
            opt_VM.prior,opt_VM.penalty,opt_VM.simulation,opt_VM.jacobian,D,opt_VM),options_VMOF),options_SD);
        disp('finished')
    % Evalutation
         for i = 1:options_SD.n_starts
            try
                Z_ODE_MS{j,i} = parameters.MS.par_evol{i};
                Z_ODE_opt(j,i,:) = parameters.MS.par_evol{i}(end,:);
                Compt_ODE(j,:)= parameters.MS.t_cpu;
                n_iter_MS(j,:) = parameters.MS.n_iter;
                Grad_MS(j,:,:) = parameters.MS.stopCrit;
                for k = 1:n_u
                    
                    [~,t{j,i,k},x_fit{j,i,k},y_fit{j,i,k}]= ...
                        simulate_RafMekErklin_woFeedback([D.t{k}(1):0.01:D.t{k}(end)],...
                        [exp(parameters.MS.par_evol{i}(end,1:n_theta)),...
                        parameters.MS.par_evol{i}(end,1+n_theta+n_sigma:end)]'...
                        ,D.conditions(k,:),1:18);
                end
                for k = 1:n_u
                    parameters.MS.sigmaInterval{i,k} = [bsxfun(@minus,y_fit{j,i,k},...
                        2*repmat(sqrt(exp(parameters.MS.par(n_theta+1:n_theta+n_sigma,i)'))...
                        ,1,size(D.measurement{1},2)/2).*exp(parameters.MS.par(end+1-size(D.measurement{1},2)-n_x:end-n_x,i))');...
                        flipud(bsxfun(@plus,y_fit{j,i,k},...
                        2*repmat(sqrt(exp(parameters.MS.par(n_theta+1:n_theta+n_sigma,i)'))...
                        ,1,size(D.measurement{1},2)/2).*exp(parameters.MS.par(end+1-size(D.measurement{1},2)-n_x:end-n_x,i))'))];
                end
            catch ME
                disp(ME.message)
            end
         end    
    parameters_SD{j} = parameters;
    clear parameters.MS
    end
end


%% newton-method
if options_SD.newtonMethod
    options_VMOF.method = 'newton-method'; %
    for j=1:length(lambda_try)
        options_VMOF.lambda = lambda_try(j);
        opt_VM.lambda = lambda_try(j);
        parameters = Manifold_opt(parameters, @(r,z) VFMO_mod(r,z,@(r,z)system_timeseriesData_JNormal_lin_v2(r,z,opt_VM.objective, ...
            opt_VM.prior,opt_VM.penalty,opt_VM.simulation,opt_VM.jacobian,D,opt_VM),options_VMOF),options_SD);
        disp('finished')
    % Evalutation
         for i = 1:options_SD.n_starts
            try
                Z_ODE_MS{j,i} = parameters.MS.par_evol{i};
                Z_ODE_opt(j,i,:) = parameters.MS.par_evol{i}(end,:);
                Compt_ODE(j,:)= parameters.MS.t_cpu;
                n_iter_MS(j,:) = parameters.MS.n_iter;
                Grad_MS(j,:,:) = parameters.MS.stopCrit;
                for k = 1:n_u
                    
                    [~,tNM{j,i,k},x_fitNM{j,i,k},y_fitNM{j,i,k}]= simulate_RafMekErklin([D.t{k}(1):0.01:D.t{k}(end)],[exp(parameters.MS.par_evol{i}(end,1:n_theta)),parameters.MS.par_evol{i}(end,1+n_theta+n_sigma:end)]',D.conditions(k,:),1:18);
                end
                for k = 1:n_u
                    parameters.MS.sigmaInterval{i,k} = [bsxfun(@minus,y_fitNM{j,i,k},...
                        2*sqrt(exp(parameters.MS.par(n_theta+1:n_theta+n_sigma,i)')));...
                        flipud(bsxfun(@plus,y_fitNM{j,i,k},2*sqrt(exp(parameters.MS.par(n_theta+1:n_theta+n_sigma,i)'))))];
                end
            catch ME
                disp(ME.message)
            end
         end
        parameters_NM{j} = parameters;
        clear parameters.MS
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
        options = optimset(options,'algorithm','interior-point','Display','off','TolFun',1e-7,'MaxIter',2000,...
                                  'MaxFunEvals',2000*n_theta);

    %% Multistart fmincon

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
    converged = zeros(options_SD.n_starts,1);
    output_FM = cell(1,options_SD.n_starts);
    for i=1:options_SD.n_starts
        try
            global errorCount
            errorCount = 100;
            T_cpu = cputime;
            [X_fmc, Jval, EF, OP] = fmincon(@(z)J_RafMekErk_normal_lin_fminconv2(z,...
                opt_VM.simulation,opt_VM.objective,opt_VM.prior,opt_VM.penalty,D,opt_VM),...
                z0(:,i),[],[],[],[],[],[],@(z)RafMekErk_Jac_fmincon(0,z(n_theta+n_sigma+1:end),z(1:n_theta+n_sigma),D.u_s,n_sigma),options);
            parameters_FM.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FM.MS.par_evol{i} = reshape(HISTORY.x,n_x+n_theta+n_sigma,[]);
            Z_FM_opt(i,:) = parameters_FM.MS.par_evol{i}(:,end)';
            J_FM_evol{i} = HISTORY.fval;
            J_FM_opt(i) = J_FM_evol{i}(end);
            parameters_FM.MS.par(:,i) = X_fmc;
            parameters_FM.MS.logPost(i) = -J_FM_opt(i);
            parameters_FM.MS.n_iter(i) = OP.iterations;
            parameters_FM.MS.n_objfun(i) = OP.funcCount;
            output_FM{i} = OP;
            try
                for k = 1:n_u
                        [~,t_FM{i,k},x_fit_FM{i,k},y_fit_FM{i,k}]= simulate_RafMekErklin([D.t{k}(1):0.01:D.t{k}(end)],...
                            [exp(parameters_FM.MS.par_evol{i}(1:n_theta,end));parameters_FM.MS.par_evol{i}(1+n_theta+n_sigma:end,end)],...
                            D.conditions(k,:),1:18);
                end
            catch
            end
            HISTORY.x = [];
            HISTORY.fval = [];
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts)])
        catch error_msg
            parameters_FM.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FM.MS.par_evol{i} = reshape(HISTORY.x,n_x+n_theta+n_sigma,[]);
            Z_FM_opt(i,:) = parameters_FM.MS.par_evol{i}(:,end)';
            J_FM_evol{i} = HISTORY.fval;
            J_FM_opt(i) = J_FM_evol{i}(end);
            parameters_FM.MS.logPost(i) = -J_FM_opt(i);
            try
                for k = 1:n_u
                        [~,t_FM{i,k},x_fit_FM{i,k},y_fit_FM{i,k}]= ...
                            simulate_RafMekErklin([D.t{k}(1):0.01:D.t{k}(end)],...
                            [exp(parameters_FM.MS.par_evol{i}(1:n_theta,end));...
                            parameters_FM.MS.par_evol{i}(1+n_theta+n_sigma:end,end)],...
                            D.conditions(k,:),1:18);
                end
                for k = 1:n_u
                    parameters_FM.MS.sigmaInterval{i,k} = [bsxfun(@minus,y_fit_FM{i,k},...
                        2*sqrt(exp(parameters_FM.MS.par(n_theta+1:n_theta+n_sigma,i)')));...
                        flipud(bsxfun(@plus,y_fit_FM{i,k},2*sqrt(exp(parameters_FM.MS.par(n_theta+1:n_theta+n_sigma,i)'))))];
                end
            catch
            end
            HISTORY.x = [];
            HISTORY.fval = [];
            converged(i) = 1;
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) ' optimization failed'])
        end
    end
end

%% Fimcon semianalytic
if options_SD.fminconSemiaOn
    global HISTORYs
        HISTORYs.x = [];
        HISTORYs.fval = [];
        optionsS = optimset('fmincon');
        optionsS = optimset(optionsS,'outputfcn',@outfuns);
        optionsS = optimset(optionsS,'GradObj','on');
        optionsS = optimset(optionsS,'algorithm','interior-point','Display','off','TolFun',1e-6,'MaxIter',2000);

    %% Multistart fmincon
    opt_VM.xTol = 1e-9;
    opt_VM.convTol = 1e-13;
    options_SD.J_old = 1e+15;
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
            J_old = options_SD.J_old;
            save('current_state','theta_old','x_0_old','J_old')
            T_cpu = cputime;
            [X_fmc, Jval, EF, OP] = fmincon(@(z)J_RafMekErk_normal_fmincon_semiav2...
                (z,opt_VM.objective,opt_VM.prior,opt_VM.penalty,opt_VM.jacobian,...
                opt_VM.simulation,D,opt_VM),...
                z0(1:n_theta+n_sigma,i),[],[],[],[],[-15*ones(n_theta+n_sigma,1)],[15*ones(n_theta+n_sigma,1)],[],optionsS);
            parameters_FMs.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FMs.MS.par_evol{i} = reshape(HISTORYs.x,n_theta+n_sigma,[]);
            J_FMs_evol{i} = HISTORYs.fval;
            J_FMs_opt(i) = J_FMs_evol{i}(end);
            parameters_FMs.MS.par(:,i) = X_fmc;
            parameters_FMs.MS.logPost(i) = -J_FMs_opt(i);
            parameters_FMs.MS.n_iter(i) = OP.iterations;
            parameters_FMs.MS.n_objfun(i) = OP.funcCount;
            output_FMs{i} = OP;
            load('current_state')
            parameters_FMs.MS.x0 = x_0_old;
            try
                for k = 1:n_u
                        [~,t_FMs{i,k},x_fit_FMs{i,k},y_fit_FMs{i,k}]= ...
                            simulate_RafMekErklin_woFeedback([D.t{k}(1):0.01:D.t{k}(end)],...
                            [exp(parameters_FMs.MS.par_evol{i}(1:n_theta,end));...
                            x_0_old]',...
                            D.conditions(k,:),1:18);
                end
            catch
            end
            HISTORYs.x = [];
            HISTORYs.fval = [];
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
        optionsa = optimset('fmincon');
        optionsa = optimset(optionsa,'outputfcn',@outfun_a);
        optionsa = optimset(optionsa,'GradObj','on');
        optionsa = optimset(optionsa,'algorithm','interior-point','Display','off',...
            'TolFun',1e-7,'MaxIter',2000,...
            'MaxFunEvals',2000*n_theta);

    xi0 = z0(1:n_theta+n_sigma,:);

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
    output_FUa =cell(1,options_SD.n_starts);
    %%
    for i=1:options_SD.n_starts
        try
            T_cpu = cputime;
            [X_fmu, Jval, EF, OP] = fmincon(@(z)J_RafMekErk_normal_fmincon_a_lin(z,@simulate_RafMekErklin_woFeedback_ana,...
                opt_VM.objective,opt_VM.prior,opt_VM.penalty,D,opt_VM),xi0(:,i),[],[],[],[],-15*ones(n_theta+n_sigma,1),15*ones(n_theta+n_sigma,1),[],optionsa);
            parameters_FUa.MS.t_cpu(i)= cputime - T_cpu;
            parameters_FUa.MS.par_evol{i} = reshape(HISTORYa.x,n_theta+n_sigma,[]);
            parameters_FUa.MS.par(:,i) = X_fmu; 
            J_FUa_evol{i} = HISTORYa.fval;
            J_FUa_opt(i) = J_FUa_evol{i}(end);
            parameters_FUa.MS.logPost(i) = -J_FUa_opt(i);
            parameters_FUa.MS.n_iter(i) = OP.iterations;
            output_FUa{i} = OP;
            try
                for k = 1:n_u
                     [~,t_FUa{i,k},x_fit_FUa{i,k},y_fit_FUa{i,k}]=...
                         simulate_RafMekErklin_woFeedback_ana(D.t{k}(1):0.01:D.t{k}(end),...
                         exp(parameters_FUa.MS.par_evol{i}(1:n_theta+n_sigma,end)),...
                         D.conditions(k,:));
                end
            catch
            end
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts)])
            HISTORYa.x = [];
            HISTORYa.fval = [];
        catch error_msg
            parameters_FUa.MS.t_cpu(i)= cputime - T_cpu;
            disp(['start ' num2str(i) '/' num2str(options_SD.n_starts) 'optimization failed'])
        end
    end
end
%% Save
save('/Results/modelComparison_new')