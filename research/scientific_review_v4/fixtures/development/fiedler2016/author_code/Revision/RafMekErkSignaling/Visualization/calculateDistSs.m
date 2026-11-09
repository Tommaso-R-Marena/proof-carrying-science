function parameters = calculateDistSs(parameters,x0,n_theta,n_sigma)
    for i = 1:length(parameters.MS.logPost)
        a1 = parameters.MS.par(n_theta+1+n_sigma:end,i);
        a2 = x0(exp(parameters.MS.par(:,i)));
        parameters.MS.distSS(i) = norm(a1(:)-a2(:));
    end
end