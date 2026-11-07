j=1;
parameters = parameters_SD{j};

for i=ind
    try
        for k = 1:n_u
            parameters.MS.sigmaInterval{i,k} = [bsxfun(@minus,bestFity{k},...
                2*repmat(sqrt(exp(parameters.MS.par(n_theta+1:n_theta+n_sigma,i)'))...
                ,1,size(D.measurement{1},2)/2).*exp(parameters.MS.par(end+1-size(D.measurement{1},2)-n_sigma-n_x:end-n_sigma-n_x,i))');...
                flipud(bsxfun(@plus,bestFity{k},...
                2*repmat(sqrt(exp(parameters.MS.par(n_theta+1:n_theta+n_sigma,i)'))...
                ,1,size(D.measurement{1},2)/2).*exp(parameters.MS.par(end+1-size(D.measurement{1},2)-n_sigma-n_x:end-n_sigma-n_x,i))'))];
        end
    catch
    end
end

parameters_SD{j}.MS.sigmaInterval = parameters.MS.sigmaInterval;