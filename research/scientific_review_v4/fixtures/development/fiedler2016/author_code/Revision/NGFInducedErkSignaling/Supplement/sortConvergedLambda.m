printBoolean = false;
alp = 0.05;

%% Gradient descent
for j=1:length(lambda_try)
    [~,indSD(j,:)] = sort(parameters_SD{j}.MS.logPost,'descend');
    indconvASD{j} = find(parameters_SD{j}.MS.distSS(indSD(j,:)) < 1e-6);
    indCritSD{j,1} = find(parameters_SD{j}.MS.stopCrit(indSD(j,:),1) < 1e-6);
    indCritSD{j,2} = find(parameters_SD{j}.MS.stopCrit(indSD(j,:),2) < 1e-6);
    % steady state converged
    indconvBSD{j} = indCritSD{j,2};
    convABSD{j} = intersect(indconvBSD{j},indconvASD{j});
    convBSD{j} = setdiff(indconvBSD{j},indconvASD{j});
    convASD{j} = setdiff(indconvASD{j},indconvBSD{j});
    notconvSD{j} = setdiff(1:100,union(indconvBSD{j},indconvASD{j}));
    percentSD(j,:) = [length(convABSD{j}),length(convBSD{j}),length(convASD{j}),length(notconvSD{j})];
    J_optSD{j} = parameters_SD{j}.MS.logPost(indconvASD{j}(1));
end

%% Newton method
% sorting and counting the starts
for j=1:length(lambda_try)
    [~,indNM(j,:)] = sort(parameters_NM{j}.MS.logPost,'descend');
    indconvANM{j} = find(parameters_NM{j}.MS.distSS(indNM(j,:)) < 1e-6);
    indCritNM{j,1} = find(parameters_NM{j}.MS.stopCrit(indNM(j,:),1) < 1e-6);
    indCritNM{j,2} = find(parameters_NM{j}.MS.stopCrit(indNM(j,:),2) < 1e-6);
    % steady state converged
    indconvBNM{j} = indCritNM{j,2};
    convABNM{j} = intersect(indconvBNM{j},indconvANM{j});
    convBNM{j} = setdiff(indconvBNM{j},indconvANM{j});
    convANM{j} = setdiff(indconvANM{j},indconvBNM{j});
    notconvNM{j} = setdiff(1:100,union(indconvBNM{j},indconvANM{j}));
    percentNM(j,:) = [length(convABNM{j}),length(convBNM{j}),length(convANM{j}),length(notconvNM{j})];
    J_optNM{j} = parameters_NM{j}.MS.logPost(indconvANM{j}(1));
end
%% FMINUNC
% sorting and counting
[~,indFUa] = sort(parameters_FUa.MS.logPost,'descend');
percentFUa = [100,0,0,0];

J_optFUa = parameters_FUa.MS.logPost(indFUa(1));
%% bound and t_effective
for j=1:length(lambda_try);
J_opt = max([J_optFUa,J_optSD{j},J_optNM{j}]);
globConvFUa = find(parameters_FUa.MS.logPost(indFUa)+chi2inv(1-alp,1)>J_opt);
globConvNM{j} = find(parameters_NM{j}.MS.logPost(indconvANM{j})+chi2inv(1-alp,1)>J_opt);
globConvSD{j} = find(parameters_SD{j}.MS.logPost(indconvASD{j})+chi2inv(1-alp,1)>J_opt);

bound = J_opt - chi2inv(1-alp,1);

t_effectiveSD(j) = sum(parameters_SD{j}.MS.t_cpu)/length(globConvSD{j});
t_effectiveNM(j) = sum(parameters_NM{j}.MS.t_cpu)/length(globConvNM{j});
t_effectiveFUa = sum(parameters_FUa.MS.t_cpu)/length(globConvFUa);
end