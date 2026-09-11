import csv
import numpy as np
import copy
import random
import matplotlib.pyplot as plt


class csv_data:

    def __init__(self, filename):

        self.filename = filename

        self.headers = []*0

        self.data = [[]*0 for i in range(0)]


        self.load_data()





    def load_data(self):

        with open(self.filename, 'r') as file:

            header_check = False

            csv_reader = csv.reader(file)
            for row in csv_reader:
                if row[0] != '':

                    if header_check:
                        if len(self.data) != len(row):
                            self.data = [[]*0 for i in range(len(row))]
                
                        for i in range(len(row)):
                            self.data[i].append(float(row[i].replace("ï»¿", "")))
                    
                    else:
                        header_check = True
                        for i in range(len(row)):
                            self.headers.append(row[i].replace("ï»¿", ""))
                    

                else:
                    break







class data_center_data:

    def __init__(self, cooling_filename, cab_filenames):

        self.cooling_data = csv_data(cooling_filename)

        self.cabinet_data = []*0

        for i in range(len(cab_filenames)):

            self.cabinet_data.append(csv_data(cab_filenames[i]))



        







    

    def gen_anon_DC(self, num_figs=None):



        anon_DC = copy.deepcopy(self)

        fig_count = 0

        for i in range(1,len(self.cooling_data.data)):

            max = np.max(self.cooling_data.data[i])

            



            for j in range(len(self.cooling_data.data[i])):

                anon_DC.cooling_data.data[i][j] = self.cooling_data.data[i][j]/max

            


            if num_figs != None and fig_count < num_figs:

                fig_count += 1

                plt.figure(fig_count)

                # plt.plot(self.cooling_data.data[0], self.cooling_data.data[i])

                plt.plot(anon_DC.cooling_data.data[0], anon_DC.cooling_data.data[i])






        for i in range(len(self.cabinet_data)):

            for j in range(1,len(self.cabinet_data[i].data)):

                max = np.max(self.cabinet_data[i].data[j])

                

                for k in range(len(self.cabinet_data[i].data[j])):

                    anon_DC.cabinet_data[i].data[j][k] = self.cabinet_data[i].data[j][k]/max

            


                if num_figs != None and fig_count < num_figs:

                    fig_count += 1

                    plt.figure(fig_count)

                    # plt.plot(self.cabinet_data[i].data[0], self.cabinet_data[i].data[j])

                    plt.plot(anon_DC.cabinet_data[i].data[0], anon_DC.cabinet_data[i].data[j])
        


        plt.show()

        return anon_DC










    def save_CSVs(self, folder="Anon_Data"):

        data_out = []

        cab_data_count = 0

        for i in range(len(self.cooling_data.data[0])+1):

            cur_row = []

            if i == 0:

                cur_row.append("time")
                cur_row.append("power")
                cur_row.append("temperature")

            else:

                cur_row.append(self.cooling_data.data[0][i-1])
                cur_row.append(self.cabinet_data[0].data[1][cab_data_count])

                if self.cabinet_data[0].data[0][cab_data_count] == self.cooling_data.data[0][i-1]:

                    cab_data_count+=1
                
                else:
                    print("Missed Cab Power Entry")
                    print([self.cabinet_data[0].data[0][cab_data_count],
                           self.cooling_data.data[0][i-1]])

                cur_row.append(self.cooling_data.data[2][i-1])
                
            
            data_out.append(cur_row)
        

        with open(folder+'/example_timeseries_scaled_w_jobs.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data_out)


        



















cooling_filename = "Summit_Thermo_Data_2020-1-20.csv"

num_cabs = 257
cab_filenames = []*0
for i in range(num_cabs):
    cab_filenames.append("cabinet_data_20200120/cab_"+str(i+1)+"_timeseries.csv")


DC = data_center_data(cooling_filename, cab_filenames)

ADC = DC.gen_anon_DC(0)

ADC.save_CSVs()

