% 
clear all
theta =[linspace(-1.5,0.19,10) ,linspace(0.2,0.9,10000), linspace(1,1.5,10)];
for i=1:10
    x(i,:) = linspace(theta(i),theta(i)+1,length(theta));
end
for i=11:length(theta)
    x(i,:) = linspace(theta(i),theta(i)+1,length(theta));
end

for i=1:length(theta)
    for j=1:length(theta)
        abl(i,j) = hysteresisODE(0,[theta(i),x(i,j)]);
    end
end

x_eq=[];
theta_eq=[];

hold on
for i=1:length(theta)
   ind_i{i}=find(abs(abl(:,i))<1e-5);
   x_eq = [x_eq;x(ind_i{i},i)];
   theta_eq = [theta_eq;theta(ind_i{i})'];
end

save('limitset','x_eq','theta_eq');