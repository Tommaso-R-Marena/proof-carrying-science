function [output] = ConversionReactionSens_u(t,z,u)
output_f = z(2)-(z(1)*u+z(2))*z(3);

output_S_theta = -(z(1)*u+z(2))*[z(4);z(5)]+[-u*z(3);1-z(3)];
output_S_x1 = -(z(1)*u+z(2))*z(6);

output = [output_f; output_S_theta; output_S_x1];
end