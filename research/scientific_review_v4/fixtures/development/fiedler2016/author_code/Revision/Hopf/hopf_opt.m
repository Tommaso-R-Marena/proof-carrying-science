clear all;
close all;
clc;

cur_dir = strrep(which('hopf_opt'),'hopf_opt.m','');
eval(['cd ' cur_dir]);

%% Data generation
theta_opt = 0;
[t,d] = ode15s(@(t,x) hopfODE(t,[theta_opt;x]),[0,30],[0;0]);
d_opt = d(end,:);
D=d_opt';

%% Options
% options system
opt_VM.simulation = @hopfODE;

% options optimization
options_SD.n_starts = 100; % number of multistarts, 100 in manuscript

options_SD.op = odeset('Events',@event,'abstol',1e-6,'reltol',1e-3);%,
options_SD.R_max = 10^12;
options_SD.maxSteps = 50000;
% options_SD.steadyState = @(theta) x0(exp(theta));

options_SD.gradientDescent = true; % false

% options VMOF
options_VMOF.retraction_factor = 'const';
lambda_try = [0.3]; %2000


%% Parameters
z0 = [theta_opt;d_opt'];

parameters.guess = z0;
parameters.min = [-4;-4;-4];
parameters.max = [4;4;4];
parameters.number = 3;

parameters.name = ['theta' 'x' 'y'];

z0 = sampleParameters(parameters,options_SD);

%% Initialisation
%% Gradient descent
if options_SD.gradientDescent
    options_VMOF.method = 'gradient-descent';
    for j=1:length(lambda_try)
        options_VMOF.lambda = lambda_try(j);
        opt_VM.lambda = lambda_try(j);
        parameters_EM = Manifold_opt(parameters, @(r,z) VFMO_mod(r,z,@(r,z) ...
            systemHopf(r,z,...
            opt_VM.simulation,D),options_VMOF),options_SD);
        parameters.start = parameters_EM.MS.par0;
    end
end

eval(['cd ' cur_dir]);
pathname = 'MS100_hopf';
save(pathname,'parameters_EM','theta_opt','d_opt');