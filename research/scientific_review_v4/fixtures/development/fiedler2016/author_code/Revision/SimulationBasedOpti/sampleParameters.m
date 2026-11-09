% sample parameters for Multistart
function [z0] = sampleParameters(varargin)
if nargin >= 1
    parameters = varargin{1};
else
    error('sampleParameters.m requires at least one inputs.')
end
rng(70);
options.n_starts = 1;
if nargin == 2
    options = setdefault(varargin{2},options);
end
% latin hypercube sampling
if options.n_starts == 1
    z0 = parameters.guess;
else
    z0 = [parameters.guess,bsxfun(@plus,parameters.min,bsxfun(@times,...
          parameters.max - parameters.min,lhsdesign(options.n_starts - size(parameters.guess,2)...
          ,parameters.number,'smooth','off')'))];
end

% start on manifold if possible
if isfield(options,'steadyState')
    for i = 1:options.n_starts
        x_0 = options.steadyState(z0(:,i));
        z0(end-length(x_0)+1:end,i) = x_0;
    end
end
