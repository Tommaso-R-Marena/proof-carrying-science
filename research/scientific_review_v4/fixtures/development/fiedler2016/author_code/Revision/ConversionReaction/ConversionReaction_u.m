function [f,grad_f] = ConversionReaction_u(t,z,u)
f = z(2)-(z(1)*u+z(2))*z(3);
grad_f = [-u*z(3) 1-z(3) -z(1)*u-z(2)];
end