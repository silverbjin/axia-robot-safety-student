// Task03 public Gazebo Harmonic ECM observer. Simulation-only; NOT E-Stop.
// Only observes the pre-existing ContactSensorData component in PostUpdate.
// No forces, transforms, ROS messages, topic publishers, or Nav2 modifications.
#include <gz/sim/System.hh>
#include <gz/sim/EntityComponentManager.hh>
#include <gz/sim/components/ContactSensorData.hh>
#include <gz/sim/components/Name.hh>
#include <gz/plugin/Register.hh>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <string>

namespace axia {
class G07S02Witness final :
  public gz::sim::System,
  public gz::sim::ISystemPostUpdate
{
 public:
  G07S02Witness() {
    const char* path=std::getenv("AXIA_G07_TASK03_WITNESS_REPORT");
    const char* sha=std::getenv("AXIA_G07_TASK03_WITNESS_SHA256");
    if(path) report_=path;
    if(sha) source_sha_=sha;
    enabled_=!report_.empty() && report_.at(0)=='/' &&
      source_sha_.size()==64 && source_sha_.find_first_not_of("0123456789abcdef")==std::string::npos;
  }

  ~G07S02Witness() override {
    if(!enabled_ || observed_iterations_<20) return;
    const std::string temp=report_+".part";
    std::ofstream out(temp,std::ios::out|std::ios::trunc);
    if(!out.good()) return;
    out << "{"
        << "\"source_sha\":\"" << source_sha_ << "\","
        << "\"sensor_found\":" << (sensor_found_?"true":"false") << ","
        << "\"report_complete\":true,"
        << "\"observed_iterations\":" << observed_iterations_ << ","
        << "\"missing_iterations\":" << missing_iterations_ << ","
        << "\"positive_contacts\":" << positive_contacts_ << ","
        << "\"first_sim_ns\":" << first_sim_ns_ << ","
        << "\"last_sim_ns\":" << last_sim_ns_ << "}\n";
    out.flush(); if(!out.good()) return;
    out.close();
    std::rename(temp.c_str(),report_.c_str());
  }

  void PostUpdate(const gz::sim::UpdateInfo &_info,
                  const gz::sim::EntityComponentManager &_ecm) override
  {
    if(!enabled_ || _info.paused) return;
    const uint64_t iter=_info.iterations;
    if(have_last_iter_ && iter>last_iter_+1)
      missing_iterations_+=(iter-last_iter_-1);
    last_iter_=iter; have_last_iter_=true;
    bool matched=false;
    int64_t count=0;
    _ecm.Each<gz::sim::components::ContactSensorData,
              gz::sim::components::Name>(
      [&](const gz::sim::Entity &,
          const gz::sim::components::ContactSensorData *_contacts,
          const gz::sim::components::Name *_name) -> bool {
        if(_name->Data()!="axia_contact") return true;
        matched=true;
        count+=_contacts->Data().contact_size();
        return true;
      });
    if(!matched) {
      if(sensor_found_) ++missing_iterations_;
      return;
    }
    const int64_t sim_ns=_info.simTime.count();
    if(!sensor_found_) first_sim_ns_=sim_ns;
    sensor_found_=true;
    last_sim_ns_=sim_ns;
    ++observed_iterations_;
    if(count>0) positive_contacts_+=count;
  }

 private:
  std::string report_;
  std::string source_sha_;
  bool enabled_{false};
  bool sensor_found_{false};
  bool have_last_iter_{false};
  uint64_t last_iter_{0};
  uint64_t observed_iterations_{0};
  uint64_t missing_iterations_{0};
  uint64_t positive_contacts_{0};
  int64_t first_sim_ns_{0};
  int64_t last_sim_ns_{0};
};
}  // namespace axia

GZ_ADD_PLUGIN(axia::G07S02Witness,
              gz::sim::System,
              gz::sim::ISystemPostUpdate)
GZ_ADD_PLUGIN_ALIAS(axia::G07S02Witness,"axia::G07S02Witness")
