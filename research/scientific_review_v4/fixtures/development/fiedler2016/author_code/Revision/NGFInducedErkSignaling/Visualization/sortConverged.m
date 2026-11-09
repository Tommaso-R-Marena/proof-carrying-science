coprintBoolean = false;
alp = 0.05;
%% Gradient descent
% sorting and counting of starts
for j=1:2%length(lambda_try)
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
    J_optSD{j} = parameters_SD{j}.MS.logPost(indSD(j,indconvASD{j}(1)));
end

%% Newton method
% sorting and counting the starts
for j=1:2 %length(lambda_try)
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
    J_optNM{j} = parameters_NM{j}.MS.logPost(indNM(j,indconvANM{j}(1)));
end

%% Hybrid
% sorting and counting
[~,indFMs] = sort(parameters_FMs.MS.logPost,'descend');
indconvAFMs = find(parameters_FMs.MS.dist_SS(indFMs) < 1e-6);
indconvBFMs = [];
for k = 1:100
    if output_FMs{indFMs(k)}.constrviolation < 1e-6
       indconvBFMs = [indconvBFMs,indFMs(k)];
    end
end
convABFMs = intersect(indconvBFMs,indconvAFMs);
convBFMs = setdiff(indconvBFMs,indconvAFMs);
convAFMs = setdiff(indconvAFMs,indconvBFMs);
notconvFMs = setdiff(1:100,union(indconvBFMs,indconvAFMs));
percentFMs = [length(convABFMs),length(convBFMs),length(convAFMs),length(notconvFMs)];

J_optFMs = parameters_FMs.MS.logPost(indFMs(indconvAFMs(1)));

%% FMINCON
% sorting and counting
[~,indFM] = sort(parameters_FM.MS.logPost,'descend');
indconvAFM = find(parameters_FM.MS.distSS(indFM) < 1e-6);
indconvBFM = [];
for k=1:100
    if output_FM{indFM(k)}.constrviolation < 1e-6
       indconvBFM = [indconvBFM,indFM(k)];
    end
end
convABFM = intersect(indconvBFM,indconvAFM);
convBFM = setdiff(indconvBFM,indconvAFM);
convAFM = setdiff(indconvAFM,indconvBFM);
notconvFM = setdiff(1:100,union(indconvBFM,indconvAFM));
percentFM = [length(convABFM),length(convBFM),length(convAFM),length(notconvFM)];

J_optFM = parameters_FM.MS.logPost(indFM(indconvAFM(1)));

%% FMINUNC
% sorting and counting
[~,indFUa] = sort(parameters_FUa.MS.logPost,'descend');
percentFUa = [100,0,0,0];

J_optFUa = parameters_FUa.MS.logPost(indFUa(1));
%% bound and t_effective
j=ind_lambda;
J_opt = max([J_optFUa,J_optFM,J_optSD{j},J_optNM{j},J_optFMs]);
globConvFUa = find(parameters_FUa.MS.logPost(indFUa)+chi2inv(1-alp,1)>J_opt);
globConvFM = find(parameters_FM.MS.logPost(indFM(indconvAFM))+chi2inv(1-alp,1)>J_opt);
globConvFMs = find(parameters_FMs.MS.logPost(indFMs(indconvAFMs))+chi2inv(1-alp,1)>J_opt);
globConvNM{j} = find(parameters_NM{j}.MS.logPost(indNM(j,indconvANM{j}))+chi2inv(1-alp,1)>J_opt);
globConvSD{j} = find(parameters_SD{j}.MS.logPost(indSD(j,indconvASD{j}))+chi2inv(1-alp,1)>J_opt);

bound = J_opt - chi2inv(1-alp,1);

t_effectiveSD = sum(parameters_SD{j}.MS.t_cpu)/length(globConvSD{j});
t_effectiveNM = sum(parameters_NM{j}.MS.t_cpu)/length(globConvNM{j});
t_effectiveFM = sum(parameters_FM.MS.t_cpu)/length(globConvFM);
t_effectiveFMs = sum(parameters_FMs.MS.t_cpu)/length(globConvFMs);
t_effectiveFUa = sum(parameters_FUa.MS.t_cpu)/length(globConvFUa);